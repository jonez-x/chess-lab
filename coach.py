"""Small, evidence-bound coach. No model is allowed to invent board facts."""
import chess
from visual_coach import scenes

NAMES = {1: 'Bauer', 2: 'Springer', 3: 'Läufer', 4: 'Turm', 5: 'Dame', 6: 'König'}
CONCEPTS = {'pawn_attack': 'Angriff mit einem Bauern', 'attack': 'Figuren angreifen',
            'development': 'Figuren entwickeln', 'king_safety': 'Königssicherheit',
            'capture': 'Schlagen und Material', 'candidate': 'Kandidaten prüfen'}


def german_san(san):
    return ''.join({'N': 'S', 'B': 'L', 'R': 'T', 'Q': 'D', 'K': 'K'}.get(c, c) for c in san)


def move_facts(before, move):
    """Facts refer to the board AFTER a legal move, never to a guessed PV."""
    assert move in before.legal_moves
    piece = before.piece_at(move.from_square)
    after = before.copy()
    after.push(move)
    source = chess.square_name(move.to_square)
    facts = []
    for target in sorted(after.attacks(move.to_square)):
        victim = after.piece_at(target)
        if victim and victim.color != piece.color and victim.piece_type != chess.KING:
            square = chess.square_name(target)
            facts.append({'id': 'attack-' + source + '-' + square, 'kind': 'attack',
                          'from': source, 'to': square,
                          'text': f'Dein {NAMES[piece.piece_type]} auf {source} greift {NAMES[victim.piece_type]} auf {square} an.'})
    if before.is_capture(move):
        captured = before.piece_at(move.to_square)
        name = NAMES[captured.piece_type] if captured else 'Bauer (en passant)'
        facts.append({'id': 'capture', 'kind': 'capture', 'text': f'Mit diesem Zug schlägst du: {name}. Das allein beweist noch keinen Materialgewinn.'})
    if before.is_castling(move):
        facts.append({'id': 'castle', 'kind': 'castle', 'text': 'Bei der Rochade ziehen König und Turm gemeinsam. Ob der König dort sicherer steht, hängt von den gegnerischen Angriffen ab.'})
    if after.is_check():
        facts.append({'id': 'check', 'kind': 'check', 'text': 'Der gegnerische König steht nach diesem Zug im Schach.'})
    if piece.piece_type in (chess.KNIGHT, chess.BISHOP) and chess.square_rank(move.from_square) in (0, 7):
        facts.append({'id': 'develop', 'kind': 'develop', 'text': 'Du bringst eine Leichtfigur von der Grundreihe ins Spiel.'})
    return facts


def lesson(before, move, kind='after', analysis=None):
    facts = move_facts(before, move)
    p = before.piece_at(move.from_square)
    attacks = [f for f in facts if f['kind'] == 'attack']
    concept = 'pawn_attack' if attacks and p.piece_type == chess.PAWN else 'attack' if attacks else 'capture' if before.is_capture(move) else 'king_safety' if before.is_castling(move) else 'development' if any(f['kind'] == 'develop' for f in facts) else 'candidate'
    return {'kind': kind, 'stage': 0, 'move': move.uci(), 'san': german_san(before.san(move)),
            'piece': NAMES[p.piece_type], 'from': chess.square_name(move.from_square),
            'to': chess.square_name(move.to_square), 'concept': concept, 'facts': facts,
            'before_fen': before.fen(), 'analysis': analysis, 'note': ''}


def candidate_line(item):
    """Replay a short engine line from the lesson root; never trust stored SAN."""
    before = chess.Board(item['before_fen'])
    move = chess.Move.from_uci(item['move'])
    if move not in before.legal_moves:
        return before, []
    candidates = (item.get('analysis') or {}).get('candidates', [])
    candidate = next((c for c in candidates if c.get('move') == move.uci()), {})
    raw = candidate.get('pv') or [move.uci()]
    if raw[0] != move.uci():
        raw = [move.uci()]
    check, moves = before.copy(), []
    for uci in raw[:3]:
        try:
            step = chess.Move.from_uci(uci)
        except ValueError:
            break
        if step not in check.legal_moves:
            break
        moves.append(step)
        check.push(step)
    return before, moves


def candidate_reply(item, language='de', concrete=False, explain=False):
    """Essential coaching comes from legal moves, not model-generated geometry."""
    before, line = candidate_line(item)
    if not line:
        return 'Bitte fordere einen neuen Hinweis an.' if language == 'de' else 'Please request a fresh hint.'
    move, de = line[0], language == 'de'
    piece = before.piece_at(move.from_square)
    name = NAMES[piece.piece_type] if de else chess.piece_name(piece.piece_type)
    accusative = 'Bauern' if de and piece.piece_type == chess.PAWN else name
    source, target = chess.square_name(move.from_square), chess.square_name(move.to_square)
    san = german_san(before.san(move)) if de else before.san(move)
    if item['kind'] == 'after':
        opening = f'Dein Zug war {san}: {name} von {source} nach {target}.' if de else f'You played {san}: {name} from {source} to {target}.'
    elif concrete:
        opening = f'Ganz konkret: Zieh deinen {accusative} von {source} nach {target} ({san}).' if de else f'Concretely: move your {name} from {source} to {target} ({san}).'
    else:
        opening = f'Mein Vorschlag ist {san}: {name} von {source} nach {target}.' if de else f'I suggest {san}: {name} from {source} to {target}.'
    effects = []
    after = before.copy()
    after.push(move)
    if before.is_check():
        effects.append('Damit hebst du das Schach auf.' if de else 'This gets your king out of check.')
    if before.is_capture(move):
        victim = before.piece_at(move.to_square)
        victim_type = victim.piece_type if victim else chess.PAWN
        captured = ('Bauern' if victim_type == chess.PAWN else NAMES[victim_type]) if de else chess.piece_name(victim_type)
        effects.append(f'Du schlägst dabei einen gegnerischen {captured}.' if de else f'You capture an opposing {captured}.')
    if before.is_castling(move):
        effects.append('König und Turm ziehen dabei gemeinsam.' if de else 'Your king and rook move together.')
    if move.promotion:
        effects.append(f'Dein Bauer wird dabei umgewandelt: {NAMES[move.promotion]}.' if de else f'Your pawn promotes to a {chess.piece_name(move.promotion)}.')
    if after.is_checkmate():
        effects.append('Das ist Schachmatt.' if de else 'This is checkmate.')
    elif after.is_check():
        effects.append('Du gibst gleichzeitig Schach.' if de else 'You also give check.')
    elif not effects:
        facts = move_facts(before, move)
        attack = next((f for f in facts if f['kind'] == 'attack'), None)
        if any(f['kind'] == 'develop' for f in facts):
            effects.append('So bringst du eine Leichtfigur von der Grundreihe ins Spiel.' if de else 'This brings a minor piece off its starting rank.')
        elif attack:
            victim = after.piece_at(chess.parse_square(attack['to']))
            target_name = NAMES[victim.piece_type] if de else chess.piece_name(victim.piece_type)
            effects.append(f'Von {target} greift die Figur den gegnerischen {target_name} auf {attack["to"]} an.' if de else f'From {target}, it attacks the opposing {target_name} on {attack["to"]}.')
    continuation = ''
    if item['kind'] == 'hint' and len(line) > 1:
        variation = before.variation_san(line)
        if de:
            variation = german_san(variation)
        continuation = ('Eine mögliche Fortsetzung aus der Engine-Suche: ' if de else 'One possible continuation from the engine search: ') + variation + '.'
        if len(line) == 3:
            reply_board = after.copy()
            reply_board.push(line[1])
            if reply_board.is_castling(line[2]):
                side = ('kurz' if chess.square_file(line[2].to_square) > 4 else 'lang') if de else ('kingside' if chess.square_file(line[2].to_square) > 4 else 'queenside')
                continuation += f' Darin kannst du anschließend {side} rochieren.' if de else f' In that line, you can then castle {side}.'
                if explain:
                    castle_target = chess.square_name(line[2].to_square)
                    opponent = 'Schwarz' if before.turn else 'Weiß'
                    response_san = german_san(after.san(line[1])) if de else after.san(line[1])
                    continuation = (f'Antwortet {opponent} mit {response_san}, ist anschließend deine {"kurze" if side == "kurz" else "lange"} Rochade legal: Dein König kommt nach {castle_target} und dein Turm ins Spiel.' if de else f'After the sample reply {response_san}, castling {side} is legal: your king goes to {castle_target} and your rook comes into play.')
    if explain and effects:
        opening = f'Der Gedanke hinter {san}:' if de else f'The idea behind {san}:'
    return ' '.join([opening] + effects[:2] + ([continuation] if continuation else []))


def english_lesson(item):
    """Stage-limited English evidence; no translation of German SAN by the LLM."""
    stage = item['stage']
    if stage == 0:
        if item['kind'] == 'hint' and item['concept'] == 'development':
            return ('The selected lesson is minor-piece development. Ask which knight or bishop '
                    'could become more active, without naming the candidate or destination. '
                    'This does not establish that other threats can safely be ignored.')
        return ('Ask the player to look for checks, captures and attacks, without naming a move.'
                if item['kind'] == 'hint' else
                'Ask what changed after the player\'s move. Do not name the target or give the answer.')
    before = chess.Board(item['before_fen'])
    move = chess.Move.from_uci(item['move'])
    piece = chess.piece_name(before.piece_type_at(move.from_square))
    if stage == 1:
        square = item['from'] if item['kind'] == 'hint' else item['to']
        return f'Ask the player to examine their {piece} on {square}. Do not name a destination or a target.'
    text = [f'The legal candidate is {before.san(move)}. It is not established as the only good move.'] if item['kind'] == 'hint' else [f'The player played {before.san(move)}.']
    after = before.copy()
    after.push(move)
    for fact in item['facts']:
        if fact['kind'] == 'attack':
            victim = chess.piece_name(after.piece_type_at(chess.parse_square(fact['to'])))
            text.append(f'After this move, the player\'s {piece} on {fact["from"]} attacks the opponent\'s {victim} on {fact["to"]}. An attack does not establish material gain or a forced reply.')
        elif fact['kind'] == 'capture':
            victim = before.piece_at(move.to_square)
            text.append(f'The move captures a {chess.piece_name(victim.piece_type) if victim else "pawn en passant"}. Net material gain is not established.')
        elif fact['kind'] == 'develop':
            text.append('The move develops a minor piece from its starting rank.')
        elif fact['kind'] == 'check':
            text.append('The opponent is in check after this move.')
        elif fact['kind'] == 'castle':
            text.append('The move is castling: king and rook move together. Improved king safety has not been established.')
    return ' '.join(text)


def present(item, level):
    """Only reveal the candidate and arrows when the user requests stage 3."""
    stage, kind = item['stage'], item['kind']
    concept = item['concept']
    attacks = [f for f in item['facts'] if f['kind'] == 'attack']
    title, text = 'Was verändert sich?', 'Welche Wirkung hat dein Zug auf die Stellung?'
    arrows = []
    marks = []
    if kind == 'hint':
        title = ['Nimm dir einen Moment.', 'Eine Spur für dich.', 'Ein Zug zum Prüfen.'][stage]
        if stage == 0:
            text = 'Prüfe zuerst Schachgebote, Schlagzüge und Angriffe. Welcher Zug kommt für dich infrage?'
            if concept == 'development':
                text = 'Welche deiner Springer oder Läufer könnten aktiver werden? Prüfe auch, was der Gegner auf deinen Zug antworten könnte.'
        elif stage == 1:
            text = f'Schau auf deinen {item["piece"]} auf {item["from"]}. Welche Möglichkeiten hat diese Figur?'
            marks = [item['from']]
        else:
            text = candidate_reply(item)
            arrows = [{'from': item['from'], 'to': item['to'], 'label': 'Zugvorschlag'}]
    else:
        if stage == 0:
            text = 'Welche gegnerische Figur greifst du mit deinem Zug an?' if attacks else 'Was verändert dein Zug? Schau auf Schläge, Angriffe und die Stellung deiner Figuren.'
        elif stage == 1:
            title = 'Schau noch einmal hin.'
            text = f'Betrachte deinen {item["piece"]} auf {item["to"]}. Welche Felder erreicht er von dort?'
            marks = [item['to']]
        else:
            title = 'Die Idee hinter dem Zug.'
            text = ' '.join(f['text'] for f in item['facts']) or 'Dein Zug ist legal. Für diese Stellung hat der Coach noch keine weitergehende belegte Erklärung.'
            if attacks:
                text += ' Ein Angriff bedeutet nicht automatisch Gewinn; der Gegner kann verschiedene Antworten haben.'
            arrows = [{'from': f['from'], 'to': f['to'], 'label': 'Angriff auf ' + f['to']} for f in attacks[:2]]
    if level == 'beginner' and stage == 2 and concept == 'pawn_attack':
        text += ' Bauern greifen schräg nach vorn an, obwohl sie geradeaus ziehen.'
    return {'kind': kind, 'stage': stage, 'title': title, 'text': text, 'concept': CONCEPTS[concept],
            'dialogue': item.get('dialogue', []), 'dialogue_intro': item.get('dialogue_intro'), 'llm_pending': bool(item.get('llm_job')),
            'llm_error': item.get('llm_error'),
            'visuals': scenes(item, item.get('llm_arrows') or arrows, item.get('llm_marks') or marks, text),
            'arrows': item.get('llm_arrows') or arrows, 'marks': item.get('llm_marks') or marks, 'note': item.get('note', ''),
            'can_retry': kind == 'after', 'revealed': stage == 2}
