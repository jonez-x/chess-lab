"""Board evidence and conversation guidance, independent of model prose."""
import re
import chess
from coach import english_lesson, candidate_reply, candidate_line, NAMES


def teaching_intent(question):
    text = question.lower().replace('’', "'")
    # Explicitly preserve the player's preference for a hint without a spoiler.
    if re.search(r"(?:nicht|noch keinen?|keine).{0,25}(?:verrat|lösung|loesung)|(?:sag|zeig|gib|verrat).{0,25}(?:nicht|keinen?|keine).{0,20}(?:zug|antwort|lösung)|nur.{0,12}(?:hinweis|tipp)|(?:don'?t|do not).{0,12}(?:tell|reveal|give|show)|no spoilers?|just a hint", text):
        return 'hint'
    if re.search(r'sag.{0,12}mir.{0,12}(?:warum|wieso|wie)\b', text):
        return 'discuss'
    if re.search(r"sag(?:e)?.{0,12}(?:mir|du)|verrat.{0,15}(?:zug|lösung)|zeig.{0,20}(?:zug|lösung)|gib.{0,15}(?:lösung|zug)|just tell|tell me (?:the|what|which)|give me (?:the|a) (?:move|answer|solution)|show (?:me )?(?:the )?(?:move|solution)", text):
        return 'solution'
    if re.search(r"keine ahnung|wei(?:ß|ss|s).{0,8}nicht|\bkp\b|no idea|don'?t know|don'?t understand|confus|don'?t get|versteh.{0,12}nicht|nicht verstehen|nicht verstanden", text):
        return 'stuck'
    if re.search(r'already|just said|repeat|schon gesagt|wiederhol|immer das gleiche', text):
        return 'repeated'
    if re.search(r'was (?:soll|sollte|kann|könnte).{0,10}ich|welchen zug|what (?:should|can|could).{0,6}i|help me|hilf mir|guide me', text):
        return 'help'
    if re.search(r'warum|wieso|wozu|\bwhy\b|explain|erklär', text):
        return 'explain'
    return 'discuss'


def response_language(question, previous='en'):
    if re.search(r'\b(?:ich|du|mir|mein|meine|was|keine|nicht|die|der|den|das|sag|sollte|gedeckt|ahnung|warum|wieso|kp)\b|weiß|weiss|versteh|könig|läufer', question, re.I):
        return 'de'
    if re.search(r'\b(?:i|you|my|what|why|which|tell|help|understand|know)\b', question, re.I):
        return 'en'
    return previous


def prepare_turn(item, question):
    """Chat requests control reveal depth just like the explicit hint buttons."""
    intent = teaching_intent(question)
    if item['kind'] == 'after' and intent in ('discuss', 'explain') and re.search(r'erklär.{0,20}(?:zug|idee)|explain.{0,20}(?:move|idea)', question, re.I):
        intent = 'solution'
    item['teaching_intent'] = intent
    item['language'] = response_language(question, item.get('language', 'en'))
    old = item['stage']
    if intent == 'solution':
        item['stage'] = 2
    elif intent == 'hint':
        item['stage'] = max(old, 1)
    elif intent in ('help', 'stuck', 'repeated'):
        item['stage'] = min(2, old + 1)
    return item['stage']


def focused_hint(item, language):
    before, line = candidate_line(item)
    if not line:
        return candidate_reply(item, language)
    move, de = line[0], language == 'de'
    name = item['piece'] if de else chess.piece_name(before.piece_type_at(move.from_square))
    accusative = 'Bauern' if de and before.piece_type_at(move.from_square) == chess.PAWN else name
    square = item['from'] if item['kind'] == 'hint' else item['to']
    if item['kind'] == 'after':
        if any(f['kind'] == 'attack' for f in item['facts']):
            return f'Dein {name} steht jetzt auf {square}. Welche gegnerische Figur greift er von dort an?' if de else f'Your {name} is now on {square}. Which opposing piece does it attack from there?'
        return f'Dein {name} steht nach deinem Zug auf {square}. Schau, was sich durch diesen Zug verändert hat.' if de else f'Your {name} is now on {square}. Look at what changed as a result of your move.'
    if de:
        start = f'Schau auf deinen {accusative} auf {square}.'
        if before.is_check():
            return start + ' Prüfe seine legalen Züge, die das Schach aufheben.'
        if before.is_capture(move):
            return start + ' Welche gegnerische Figur kann er schlagen?'
        if any(f['kind'] == 'develop' for f in item['facts']):
            return start + ' Er steht noch auf der Grundreihe. Wie kannst du ihn ins Spiel bringen?'
        if any(f['kind'] == 'check' for f in item['facts']):
            return start + ' Kannst du mit ihm Schach geben?'
        if any(f['kind'] == 'attack' for f in item['facts']):
            return start + ' Suche einen Zug, mit dem er eine gegnerische Figur angreift.'
        return start + ' Prüfe, welche Felder diese Figur erreichen kann.'
    start = f'Focus on your {name} on {square}.'
    if before.is_check():
        return start + ' Look at its legal moves that get your king out of check.'
    if before.is_capture(move):
        return start + ' Which opposing piece can it capture?'
    if any(f['kind'] == 'develop' for f in item['facts']):
        return start + ' It is still on its starting rank. How can you bring it into play?'
    if any(f['kind'] == 'check' for f in item['facts']):
        return start + ' Can you give check with it?'
    if any(f['kind'] == 'attack' for f in item['facts']):
        return start + ' Look for a move that attacks an opposing piece.'
    return start + ' Look at the squares this piece can reach.'


def context(board, color, item, question):
    language = response_language(question, item.get('language', 'en'))
    intent = item.get('teaching_intent') or teaching_intent(question)
    expected = chess.Board(item['before_fen'])
    if item['kind'] == 'after':
        expected.push(chess.Move.from_uci(item['move']))
    if board.fen() != expected.fen():
        return {'facts': ['The saved lesson is for a different position.'], 'history': [],
                'guidance': 'Request a fresh hint; do not recommend the stale candidate.',
                'language': language, 'arrows': [], 'marks': [],
                'direct_reply': 'Die Stellung hat sich geändert. Fordere bitte einen neuen Hinweis an.' if language == 'de' else 'The position has changed. Please request a fresh hint.'}
    player = color == 'white'
    king = board.king(player)
    checkers = sorted(board.attackers(not player, king)) if king is not None else []
    def describe(square):
        p = board.piece_at(square)
        return f'{"white" if p.color else "black"} {chess.piece_name(p.piece_type)} on {chess.square_name(square)}'
    facts = [f'The player controls {color}. It is {"white" if board.turn else "black"} to move.',
             'Current player pieces: ' + ', '.join(describe(s) for s,p in board.piece_map().items() if p.color == player),
             'Player king is ' + ('in check.' if checkers else 'NOT in check.'),
             'Revealed lesson: ' + english_lesson(item)]
    discussion = question.lower() + ' ' + ' '.join(m['text'].lower() for m in item.get('dialogue', []) if m['role'] == 'user')
    for square, piece in sorted(board.piece_map().items()):
        if piece.color != player:
            continue
        if checkers and piece.piece_type != chess.KING and chess.piece_name(piece.piece_type) not in discussion:
            continue
        attackers = sorted(board.attackers(not player, square))
        if attackers:
            facts.append(describe(square) + ' is attacked by ' + ', '.join(describe(s) for s in attackers) + '.')
    facts.append('Attack relations are geometric; they do not establish legal captures, material loss or a forced reply. They do not rank threats or establish that a piece needs defending. It is also not established that ignoring an attack is safe.')
    categories = set()
    if checkers:
        facts.append('Check must be resolved before any other threat. Possible categories are capturing the checking piece, blocking a sliding check, or moving the king; not all categories are necessarily legal here. Castling out of check is illegal.')
        if board.turn == player:
            for move in board.legal_moves:
                if board.is_capture(move) and (move.to_square in checkers or board.is_en_passant(move)):
                    categories.add('capture the checking piece')
                elif board.piece_type_at(move.from_square) == chess.KING:
                    categories.add('move the king to safety')
                else:
                    categories.add('block the checking line')
            facts.append('Exhaustive legal response categories in THIS position: ' + (', '.join(sorted(categories)) or 'none; the game is over') + '. Do not suggest an unavailable category.' + (' Exact moves are withheld at this hint stage.' if item['stage'] < 2 else ''))
    history = list(item.get('dialogue', []))
    if history and history[-1]['role'] == 'user' and history[-1]['text'] == question:
        history = history[:-1]
    confused = intent == 'stuck'
    repeated = bool(re.search(r'already|just said|repeat|schon gesagt|wiederhol', question, re.I))
    guidance = 'Respond to the latest thought. Check claims against board evidence. Do not ask the player to identify attackers they have already named. For check, use ONLY the legal response categories in the evidence. Do not bring up unrelated attacked pieces.'
    guidance += (' The candidate is revealed; use it to give a concrete answer and explain the checked continuation. Do not ask another discovery question.' if item['stage'] == 2 else ' Do not reveal a candidate destination at this hint stage.')
    if not checkers:
        guidance += ' For general advice, focus on the revealed lesson, not an inventory of attacks. Never turn geometric attacks into a recommendation to defend or move those pieces. If asked whether defense is necessary, explain that the resulting continuation must be evaluated; do not claim it is necessary or safe to ignore based only on attack relations.'
    if repeated:
        guidance = 'Apologize in a few words, then give a concrete thinking step, not a repeated summary. For a king move, tell the player to examine neighboring squares and rule out those attacked by an opponent. Do not repeat who attacks whom or ask for attacker names. Do not name a solution square.'
    if confused:
        guidance = 'Explain what the previous instruction MEANS, not the same instruction again. For a king move, explain that safe means a square no opposing piece attacks, and that saving another piece can wait until the king is safe. Do not ask a question, list unrelated attacks, use jargon, or name a solution square. Two short sentences.'
    if (confused or repeated) and not checkers:
        guidance = 'Explain the revealed lesson more concretely. Do not ask the same question again, invent a king emergency, or list unrelated attacks.'
    arrows, marks = [], []
    if checkers and (confused or repeated or re.search(r'king|check|könig|schach', question, re.I)):
        marks = [chess.square_name(king)]
        arrows = [{'from': chess.square_name(s), 'to': chess.square_name(king), 'label': 'Check'} for s in checkers]
    direct_reply = None
    general_hint = bool(re.search(r'what should i do|what (?:can|should) i play|guiding question|was soll ich|welchen zug', question, re.I))
    if (not checkers and item['kind'] == 'hint' and item['stage'] == 0
            and item['concept'] == 'development' and general_hint):
        direct_reply = ('Let’s look at development: which of your knights or bishops could become more active? '
                        'Before choosing a move, check what your opponent could capture in reply.')
    if categories == {'move the king to safety'}:
        if repeated:
            direct_reply = "You're right, you already identified the attackers. Next, look at the squares next to your king and rule out any that an opponent attacks; here, only moving the king can get you out of check."
        if confused:
            direct_reply = "A safe square is one where no opposing piece can attack your king. Here you must move your king to such a square first; your bishop has to wait."
            if 'bishop' not in discussion:
                direct_reply = "A safe square is one where no opposing piece can attack your king. Here you must move your king to such a square first; other threats have to wait."
    if item['stage'] == 2:
        # The PV is disclosed only after the user requests the solution or gets stuck again.
        explanation = candidate_reply(item, language, concrete=intent in ('stuck', 'repeated'), explain=intent == 'explain')
        facts.append('Verified candidate explanation: ' + candidate_reply(item, 'en'))
        if intent in ('solution', 'help', 'stuck', 'repeated', 'hint') or (intent == 'explain' and re.search(r'dies.{0,8}zug|der zug|dem zug|this move|that move|the move', question, re.I)):
            direct_reply = explanation
        if item['kind'] == 'hint':
            arrows = [{'from': item['from'], 'to': item['to'], 'label': 'Zugvorschlag' if language == 'de' else 'Suggested move'}]
            marks = [item['from'], item['to']]
    elif item['stage'] == 1 and intent in ('solution', 'help', 'stuck', 'repeated', 'hint'):
        direct_reply = focused_hint(item, language)
        marks = [item['from'] if item['kind'] == 'hint' else item['to']]
    # Describe defenders as geometry too; defended does not imply a favorable exchange.
    if re.search(r'defend|protect|gedeckt|deck|verteidig', question, re.I):
        described = []
        for square, piece in sorted(board.piece_map().items()):
            if piece.color == player and piece.piece_type != chess.KING and board.attackers(not player, square):
                defenders = sorted(board.attackers(player, square))
                facts.append(describe(square) + ' has geometric defenders: ' + (', '.join(describe(s) for s in defenders) or 'none') + '. A pinned defender may be unable to recapture; this is not a safety verdict.')
                if len(described) < 2:
                    target = chess.square_name(square)
                    if language == 'de':
                        labels = ', '.join(f'{NAMES[board.piece_type_at(s)]} {chess.square_name(s)}' for s in defenders)
                        described.append(f'Dein {NAMES[piece.piece_type]} auf {target} ' + (f'ist gedeckt durch {labels}.' if defenders else 'hat keinen eigenen Verteidiger.'))
                    else:
                        labels = ', '.join(f'{chess.piece_name(board.piece_type_at(s))} {chess.square_name(s)}' for s in defenders)
                        described.append(f'Your {chess.piece_name(piece.piece_type)} on {target} ' + (f'is defended by {labels}.' if defenders else 'has no defender.'))
        guidance += ' Address the defense claim directly. Do not repeat a generic instruction to create threats. Explain that exchange values and legal recaptures matter, without asserting that all pieces are safe.'
        if intent in ('discuss', 'explain'):
            caveat = ('Gedeckt heißt aber nicht automatisch, dass ein Rückschlag legal oder der Abtausch günstig ist.' if language == 'de' else 'Being defended does not automatically make a recapture legal or an exchange favorable.')
            direct_reply = ' '.join(described + [caveat])
    return {'facts': facts, 'history': history[-8:], 'guidance': guidance, 'direct_reply': direct_reply,
            'language': language, 'fallback_reply': candidate_reply(item, language) if item['stage'] == 2 else focused_hint(item, language) if item['stage'] == 1 else None,
            'arrows': arrows, 'marks': marks}
