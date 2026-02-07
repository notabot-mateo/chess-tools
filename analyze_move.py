"""
Pre-Move Analysis
Before making a move, check for common blunders and tactical issues.
"""

from typing import List, Tuple, Dict, Optional
from board import Board, Square, Piece, PieceType, Color, sq
from attacks import (
    get_attackers, get_defenders, is_hanging, is_attacked,
    find_hanging_pieces, analyze_square, get_attacked_by_piece
)


# Piece values for exchange calculations
PIECE_VALUES = {
    PieceType.PAWN: 1,
    PieceType.KNIGHT: 3,
    PieceType.BISHOP: 3,
    PieceType.ROOK: 5,
    PieceType.QUEEN: 9,
    PieceType.KING: 1000,  # Can't really capture, but useful for checks
}


def get_piece_value(piece: Piece) -> int:
    """Get the material value of a piece."""
    return PIECE_VALUES[piece.piece_type]


def simulate_move(board: Board, from_sq: Square, to_sq: Square) -> Board:
    """
    Create a new board with the move made.
    Does not validate legality - just moves the piece.
    """
    # Create a copy
    new_board = Board()
    new_board.pieces = board.pieces.copy()
    new_board.turn = board.turn.opposite
    new_board.castling_rights = board.castling_rights
    new_board.en_passant = None
    new_board.halfmove_clock = board.halfmove_clock
    new_board.fullmove_number = board.fullmove_number
    
    piece = new_board.pieces.pop(from_sq.index, None)
    if piece:
        new_board.pieces[to_sq.index] = piece
    
    return new_board


def analyze_move(board: Board, from_sq: Square, to_sq: Square) -> Dict:
    """
    Comprehensive pre-move analysis.
    
    Returns dict with:
        - piece: The piece being moved
        - capture: The piece being captured (if any)
        - destination_attacked: Is the destination square attacked by enemy?
        - attackers: What pieces attack the destination?
        - defenders_after: What friendly pieces will defend after the move?
        - pieces_left_hanging: What pieces are left undefended by this move?
        - is_check: Does this move give check?
        - exchange_analysis: If capturing, what happens in the exchange?
        - warnings: List of potential issues
    """
    piece = board.get(from_sq)
    if piece is None:
        return {'error': f'No piece on {from_sq}'}
    
    capture = board.get(to_sq)
    color = piece.color
    enemy_color = color.opposite
    
    # Simulate the move
    after_board = simulate_move(board, from_sq, to_sq)
    
    # What attacks the destination?
    attackers = get_attackers(board, to_sq, by_color=enemy_color)
    
    # What defends the destination after the move?
    defenders_after = get_defenders(after_board, to_sq)
    
    # What pieces become hanging after this move?
    # Check all our pieces that were defended by the moving piece
    pieces_left_hanging = []
    for sq_idx, p in board.pieces.items():
        if p.color == color and sq_idx != from_sq.index:
            sq_obj = Square(sq_idx)
            # Was it defended before?
            defenders_before = get_defenders(board, sq_obj)
            was_defended_by_moving = any(d[0].index == from_sq.index for d in defenders_before)
            
            if was_defended_by_moving:
                # Is it still defended after?
                defenders_now = get_defenders(after_board, sq_obj)
                # Is it attacked?
                enemies = get_attackers(after_board, sq_obj, by_color=enemy_color)
                
                if len(enemies) > 0 and len(defenders_now) == 0:
                    pieces_left_hanging.append((sq_obj, p))
    
    # Does this give check?
    enemy_king_sq = after_board.find_king(enemy_color)
    is_check = False
    if enemy_king_sq:
        is_check = is_attacked(after_board, enemy_king_sq, by_color=color)
    
    # Exchange analysis if capturing
    exchange_analysis = None
    if capture:
        gain = get_piece_value(capture)
        
        # What can recapture?
        recapturers = get_attackers(after_board, to_sq, by_color=enemy_color)
        
        if recapturers:
            # Simplistic: assume lowest value piece recaptures
            lowest_recapturer = min(recapturers, key=lambda x: get_piece_value(x[1]))
            loss = get_piece_value(piece)
            
            # Do we have enough defenders?
            net = gain - loss if len(defenders_after) < len(recapturers) else gain
            
            exchange_analysis = {
                'capturing': str(piece),
                'captured': str(capture),
                'gain': gain,
                'potential_loss': loss,
                'recapturers': [(s.name, str(p)) for s, p in recapturers],
                'our_defenders': [(s.name, str(p)) for s, p in defenders_after],
                'likely_net': net if len(recapturers) > 0 else gain,
                'safe': len(defenders_after) >= len(recapturers),
            }
        else:
            exchange_analysis = {
                'capturing': str(piece),
                'captured': str(capture),
                'gain': gain,
                'recapturers': [],
                'safe': True,
            }
    
    # Generate warnings
    warnings = []
    
    if attackers and not capture:
        # Moving to an attacked square without capturing
        if not defenders_after:
            warnings.append(f"⚠️ {piece} moves to {to_sq} which is attacked and will be undefended!")
        elif len(attackers) > len(defenders_after):
            warnings.append(f"⚠️ {to_sq} has more attackers ({len(attackers)}) than defenders ({len(defenders_after)})")
    
    if exchange_analysis and not exchange_analysis.get('safe', True):
        warnings.append(f"⚠️ Capture on {to_sq} may lose material (recapture possible)")
    
    if pieces_left_hanging:
        for sq_obj, p in pieces_left_hanging:
            warnings.append(f"⚠️ {p} on {sq_obj} will be left hanging!")
    
    # Check if we're moving away from defending our king (basic king safety)
    our_king_sq = board.find_king(color)
    if our_king_sq:
        king_defenders_before = get_defenders(board, our_king_sq)
        was_defending_king = any(d[0].index == from_sq.index for d in king_defenders_before)
        if was_defending_king:
            king_defenders_after = get_defenders(after_board, our_king_sq)
            if len(king_defenders_after) < len(king_defenders_before):
                warnings.append(f"⚠️ This move weakens king defense")
    
    return {
        'move': f'{piece}{from_sq}-{to_sq}' + ('x' + str(capture) if capture else ''),
        'piece': str(piece),
        'from': from_sq.name,
        'to': to_sq.name,
        'capture': str(capture) if capture else None,
        'destination_attacked_by': [(s.name, str(p)) for s, p in attackers],
        'defenders_after_move': [(s.name, str(p)) for s, p in defenders_after],
        'pieces_left_hanging': [(s.name, str(p)) for s, p in pieces_left_hanging],
        'gives_check': is_check,
        'exchange_analysis': exchange_analysis,
        'warnings': warnings,
    }


def quick_check(board: Board, from_sq: Square, to_sq: Square) -> str:
    """
    Quick human-readable summary of a move.
    """
    analysis = analyze_move(board, from_sq, to_sq)
    
    if 'error' in analysis:
        return analysis['error']
    
    lines = [f"Move: {analysis['move']}"]
    
    if analysis['gives_check']:
        lines.append("✓ Gives check!")
    
    if analysis['exchange_analysis']:
        ea = analysis['exchange_analysis']
        if ea.get('safe'):
            lines.append(f"✓ Safe capture (+{ea['gain']})")
        else:
            lines.append(f"? Capture may trade: +{ea['gain']} but -{ea['potential_loss']}")
    
    for warning in analysis['warnings']:
        lines.append(warning)
    
    if not analysis['warnings']:
        lines.append("✓ No obvious issues")
    
    return "\n".join(lines)


def check_all_hanging(board: Board, color: Color) -> str:
    """Quick report of all hanging pieces for a color."""
    hanging = find_hanging_pieces(board, color)
    if not hanging:
        return f"No hanging pieces for {'White' if color == Color.WHITE else 'Black'}"
    
    lines = [f"⚠️ Hanging pieces for {'White' if color == Color.WHITE else 'Black'}:"]
    for sq_obj, piece in hanging:
        attackers = get_attackers(board, sq_obj, by_color=color.opposite)
        lines.append(f"  {piece} on {sq_obj} - attacked by {[(s.name, str(p)) for s, p in attackers]}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("=== Move Analysis Tests ===\n")
    
    # Position: 1.e4 e5 2.Nf3 - black to move
    fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2"
    board = Board.from_fen(fen)
    print(board)
    print()
    
    # Check hanging pieces
    print(check_all_hanging(board, Color.BLACK))
    print()
    
    # Analyze defending the pawn with Nc6
    print("--- Analyzing Nc6 (defending e5) ---")
    print(quick_check(board, sq('b8'), sq('c6')))
    print()
    
    # What if black plays d6 instead?
    print("--- Analyzing d6 (supporting e5) ---")
    print(quick_check(board, sq('d7'), sq('d6')))
    print()
    
    # Bad move: Qf6 (doesn't help e5)
    print("--- Analyzing Qf6 (leaves e5 hanging) ---")
    print(quick_check(board, sq('d8'), sq('f6')))
    print()
    
    # Test a capture scenario
    print("\n=== Capture Analysis ===")
    # Position where knight can take but will be recaptured
    fen2 = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
    board2 = Board.from_fen(fen2)
    print(board2)
    print()
    
    print("--- Analyzing Nxe5 ---")
    result = analyze_move(board2, sq('f3'), sq('e5'))
    print(f"Move: {result['move']}")
    print(f"Exchange: {result['exchange_analysis']}")
    print(f"Warnings: {result['warnings']}")
