"""
Attack and Defense Analysis
Query what pieces attack or defend any square on the board.
"""

from typing import List, Tuple, Set
from board import Board, Square, Piece, PieceType, Color, sq


# Movement patterns for each piece type
KNIGHT_OFFSETS = [
    (1, 2), (2, 1), (2, -1), (1, -2),
    (-1, -2), (-2, -1), (-2, 1), (-1, 2)
]

KING_OFFSETS = [
    (0, 1), (1, 1), (1, 0), (1, -1),
    (0, -1), (-1, -1), (-1, 0), (-1, 1)
]

# Sliding piece directions
BISHOP_DIRECTIONS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ROOK_DIRECTIONS = [(0, 1), (0, -1), (1, 0), (-1, 0)]
QUEEN_DIRECTIONS = BISHOP_DIRECTIONS + ROOK_DIRECTIONS


def get_attackers(board: Board, target: Square, by_color: Color = None) -> List[Tuple[Square, Piece]]:
    """
    Find all pieces that attack a given square.
    
    Args:
        board: The chess board
        target: The square being attacked
        by_color: Optional - only return attackers of this color
    
    Returns:
        List of (square, piece) tuples for each attacker
    """
    attackers = []
    
    # Check for knight attackers
    for offset in KNIGHT_OFFSETS:
        attacker_sq = target.offset(offset[0], offset[1])
        if attacker_sq:
            piece = board.get(attacker_sq)
            if piece and piece.piece_type == PieceType.KNIGHT:
                if by_color is None or piece.color == by_color:
                    attackers.append((attacker_sq, piece))
    
    # Check for king attackers
    for offset in KING_OFFSETS:
        attacker_sq = target.offset(offset[0], offset[1])
        if attacker_sq:
            piece = board.get(attacker_sq)
            if piece and piece.piece_type == PieceType.KING:
                if by_color is None or piece.color == by_color:
                    attackers.append((attacker_sq, piece))
    
    # Check for pawn attackers
    # White pawns attack diagonally upward, black pawns attack diagonally downward
    for color, rank_dir in [(Color.WHITE, -1), (Color.BLACK, 1)]:
        if by_color is not None and by_color != color:
            continue
        for file_dir in [-1, 1]:
            attacker_sq = target.offset(file_dir, rank_dir)
            if attacker_sq:
                piece = board.get(attacker_sq)
                if piece and piece.piece_type == PieceType.PAWN and piece.color == color:
                    attackers.append((attacker_sq, piece))
    
    # Check for sliding piece attackers (bishop, rook, queen)
    def check_sliding(directions: List[Tuple[int, int]], valid_types: Set[PieceType]):
        for dx, dy in directions:
            current = target
            while True:
                next_sq = current.offset(dx, dy)
                if next_sq is None:
                    break
                piece = board.get(next_sq)
                if piece:
                    if piece.piece_type in valid_types:
                        if by_color is None or piece.color == by_color:
                            attackers.append((next_sq, piece))
                    break  # Blocked by any piece
                current = next_sq
    
    # Diagonal sliders (bishop, queen)
    check_sliding(BISHOP_DIRECTIONS, {PieceType.BISHOP, PieceType.QUEEN})
    
    # Orthogonal sliders (rook, queen)
    check_sliding(ROOK_DIRECTIONS, {PieceType.ROOK, PieceType.QUEEN})
    
    return attackers


def get_defenders(board: Board, target: Square) -> List[Tuple[Square, Piece]]:
    """
    Find all pieces that defend the piece on a given square.
    
    A defender is a friendly piece that could recapture if the piece is taken.
    This is essentially: what friendly pieces attack this square?
    
    Returns empty list if the square is empty.
    """
    piece = board.get(target)
    if piece is None:
        return []
    
    return get_attackers(board, target, by_color=piece.color)


def is_attacked(board: Board, target: Square, by_color: Color) -> bool:
    """Check if a square is attacked by the given color."""
    return len(get_attackers(board, target, by_color=by_color)) > 0


def is_defended(board: Board, target: Square) -> bool:
    """Check if the piece on this square has at least one defender."""
    return len(get_defenders(board, target)) > 0


def is_hanging(board: Board, target: Square) -> bool:
    """
    Check if a piece is hanging (undefended and attacked).
    
    Returns False if square is empty.
    """
    piece = board.get(target)
    if piece is None:
        return False
    
    enemy_color = piece.color.opposite
    attackers = get_attackers(board, target, by_color=enemy_color)
    defenders = get_defenders(board, target)
    
    return len(attackers) > 0 and len(defenders) == 0


def is_protected(board: Board, target: Square) -> bool:
    """
    Check if a piece is adequately protected (defenders >= attackers).
    
    Note: This is a simplified check - doesn't account for piece values.
    A piece defended by a queen against an attacking pawn isn't really "protected"
    since you'd lose material in the exchange.
    
    Returns True if square is empty (nothing to protect).
    """
    piece = board.get(target)
    if piece is None:
        return True
    
    enemy_color = piece.color.opposite
    attackers = get_attackers(board, target, by_color=enemy_color)
    defenders = get_defenders(board, target)
    
    return len(defenders) >= len(attackers)


def attack_count(board: Board, target: Square, by_color: Color) -> int:
    """Count how many pieces of a color attack a square."""
    return len(get_attackers(board, target, by_color=by_color))


def defense_count(board: Board, target: Square) -> int:
    """Count how many pieces defend the piece on a square."""
    return len(get_defenders(board, target))


def get_all_attacked_squares(board: Board, by_color: Color) -> Set[Square]:
    """Get all squares attacked by pieces of a given color."""
    attacked = set()
    for square_idx, piece in board.pieces.items():
        if piece.color == by_color:
            # Get all squares this piece attacks
            attacked.update(get_attacked_by_piece(board, Square(square_idx), piece))
    return attacked


def get_attacked_by_piece(board: Board, from_square: Square, piece: Piece) -> Set[Square]:
    """Get all squares attacked by a specific piece."""
    attacked = set()
    
    if piece.piece_type == PieceType.KNIGHT:
        for offset in KNIGHT_OFFSETS:
            target = from_square.offset(offset[0], offset[1])
            if target:
                attacked.add(target)
    
    elif piece.piece_type == PieceType.KING:
        for offset in KING_OFFSETS:
            target = from_square.offset(offset[0], offset[1])
            if target:
                attacked.add(target)
    
    elif piece.piece_type == PieceType.PAWN:
        # Pawns attack diagonally
        rank_dir = 1 if piece.color == Color.WHITE else -1
        for file_dir in [-1, 1]:
            target = from_square.offset(file_dir, rank_dir)
            if target:
                attacked.add(target)
    
    elif piece.piece_type in (PieceType.BISHOP, PieceType.QUEEN):
        for dx, dy in BISHOP_DIRECTIONS:
            current = from_square
            while True:
                target = current.offset(dx, dy)
                if target is None:
                    break
                attacked.add(target)
                if board.get(target):  # Blocked
                    break
                current = target
    
    if piece.piece_type in (PieceType.ROOK, PieceType.QUEEN):
        for dx, dy in ROOK_DIRECTIONS:
            current = from_square
            while True:
                target = current.offset(dx, dy)
                if target is None:
                    break
                attacked.add(target)
                if board.get(target):  # Blocked
                    break
                current = target
    
    return attacked


def find_hanging_pieces(board: Board, color: Color) -> List[Tuple[Square, Piece]]:
    """Find all hanging pieces of the given color."""
    hanging = []
    for square, piece in board.get_pieces_by_color(color):
        if is_hanging(board, square):
            hanging.append((square, piece))
    return hanging


def find_undefended_pieces(board: Board, color: Color) -> List[Tuple[Square, Piece]]:
    """Find all undefended pieces of the given color (even if not attacked)."""
    undefended = []
    for square, piece in board.get_pieces_by_color(color):
        if not is_defended(board, square):
            undefended.append((square, piece))
    return undefended


def analyze_square(board: Board, target: Square) -> dict:
    """
    Get a complete analysis of a square.
    
    Returns dict with:
        - piece: The piece on this square (or None)
        - white_attackers: List of white pieces attacking
        - black_attackers: List of black pieces attacking
        - defenders: List of friendly pieces defending
        - is_hanging: True if attacked and undefended
        - is_protected: True if defenders >= attackers
    """
    piece = board.get(target)
    white_attackers = get_attackers(board, target, by_color=Color.WHITE)
    black_attackers = get_attackers(board, target, by_color=Color.BLACK)
    
    if piece:
        enemy_color = piece.color.opposite
        enemy_attackers = white_attackers if enemy_color == Color.WHITE else black_attackers
        defenders = get_defenders(board, target)
        hanging = len(enemy_attackers) > 0 and len(defenders) == 0
        protected = len(defenders) >= len(enemy_attackers)
    else:
        defenders = []
        hanging = False
        protected = True
    
    return {
        'square': target.name,
        'piece': str(piece) if piece else None,
        'white_attackers': [(s.name, str(p)) for s, p in white_attackers],
        'black_attackers': [(s.name, str(p)) for s, p in black_attackers],
        'defenders': [(s.name, str(p)) for s, p in defenders],
        'is_hanging': hanging,
        'is_protected': protected,
    }


if __name__ == "__main__":
    # Test with the starting position
    print("=== Starting Position Analysis ===\n")
    board = Board.starting_position()
    print(board)
    
    # Test e4 square
    print("\n--- Analysis of e4 ---")
    result = analyze_square(board, sq('e4'))
    print(f"Piece: {result['piece']}")
    print(f"White attackers: {result['white_attackers']}")
    print(f"Black attackers: {result['black_attackers']}")
    
    # Test e2 pawn
    print("\n--- Analysis of e2 (white pawn) ---")
    result = analyze_square(board, sq('e2'))
    print(f"Piece: {result['piece']}")
    print(f"Defenders: {result['defenders']}")
    print(f"Is protected: {result['is_protected']}")
    
    # Create a position where a piece is hanging
    print("\n\n=== Test Position: Hanging Piece ===")
    # After 1.e4 e5 2.Nf3 - the e5 pawn is defended by d7/f7 pawns
    test_fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2"
    board2 = Board.from_fen(test_fen)
    print(board2)
    
    print("\n--- Analysis of e5 (black pawn) ---")
    result = analyze_square(board2, sq('e5'))
    print(f"Piece: {result['piece']}")
    print(f"White attackers: {result['white_attackers']}")
    print(f"Defenders: {result['defenders']}")
    print(f"Is hanging: {result['is_hanging']}")
    print(f"Is protected: {result['is_protected']}")
    
    # Find all hanging pieces
    print("\n--- Hanging pieces (black) ---")
    for s, p in find_hanging_pieces(board2, Color.BLACK):
        print(f"  {p} on {s}")
