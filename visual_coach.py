"""Visual explanations derived from the displayed board, never model coordinates."""
import chess


def scenes(item, arrows, marks, text):
    board = chess.Board(item['before_fen'])
    player = board.turn
    if item['kind'] == 'after':
        board.push(chess.Move.from_uci(item['move']))
    king = board.king(player)
    checkers = sorted(board.attackers(not player, king)) if king is not None else []
    result = []
    if checkers:
        result.append({'title': 'Schach verstehen',
                       'text': 'Diese Figuren greifen deinen König an. Dein nächster Zug muss das Schach aufheben.',
                       'marks': [chess.square_name(king)],
                       'arrows': [{'from': chess.square_name(s), 'to': chess.square_name(king), 'label': 'Schach'} for s in checkers]})
    if item['concept'] == 'development' and item['stage'] == 0 and not checkers:
        squares = [chess.square_name(s) for s, p in sorted(board.piece_map().items())
                   if p.color == player and p.piece_type in (chess.KNIGHT, chess.BISHOP)]
        result.append({'title': 'Figuren aktivieren',
                       'text': 'Betrachte deine markierten Springer und Läufer. Welche Figur könnte aktiver werden? Prüfe danach die möglichen Antworten des Gegners.',
                       'marks': squares, 'arrows': []})
    else:
        result.append({'title': 'Dein Lernhinweis', 'text': text, 'arrows': arrows, 'marks': marks})
    # Existing opponent attacks are observable facts, not candidate-move spoilers.
    for square, piece in sorted(board.piece_map().items()):
        if piece.color != player or piece.piece_type == chess.KING or checkers:
            continue
        attackers = sorted(board.attackers(not player, square))
        if not attackers:
            continue
        target = chess.square_name(square)
        result.append({'title': 'Angriff auf ' + target,
                       'text': f'Die Pfeile zeigen gegnerische Angriffe auf {target}. Angegriffen heißt nicht automatisch verloren oder verteidigungspflichtig: Entscheidend ist die Fortsetzung nach einem Schlagzug.',
                       'marks': [target],
                       'arrows': [{'from': chess.square_name(s), 'to': target, 'label': 'Angriff auf ' + target} for s in attackers]})
    return result
