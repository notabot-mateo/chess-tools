"""
Tactical Pattern Detection
Find forks, pins, skewers, and discovered attack opportunities.
"""

from typing import List, Tuple, Dict, Set, Optional
from board import Board, Square, Piece, PieceType, Color, sq
from attacks import (
    get_attackers, get_defenders, get_attacked_by_piece,
    is_attacked, KNIGHT_OFFSETS, BISHOP_DIRECTIONS, ROOK_DIRECTIONS,
    QUEEN_DIRECTIONS, KING_OFFSETS
)


# Piece values for tactical evaluation
PIECE_VALUES = {
    PieceType.PAWN: 1,
    PieceType.KNIGHT: 3,
    PieceType.BISHOP: 3,
    PieceType.ROOK: 5,
    PieceType.QUEEN: 9,
    PieceType.KING: 100,  # High but not infinite for comparisons
}


def get_piece_value(piece: Piece) -> int:
    return PIECE_VALUES[piece.piece_type]


# =============================================================================
# FORKS - A piece attacking two or more enemy pieces simultaneously
# =============================================================================

def find_forks(board: Board, color: Color) -> List[Dict]:
    """
    Find all pieces of the given color that are currently forking enemy pieces.
    
    Returns list of dicts with:
        - forking_piece: The piece doing the forking
        - forking_square: Where it sits
        - targets: List of enemy pieces being forked
        - total_value: Combined value of forked pieces
    """
    forks = []
    enemy_color = color.opposite
    
    for square, piece in board.get_pieces_by_color(color):
        # Get all squares this piece attacks
        attacked = get_attacked_by_piece(board, square, piece)
        
        # Find enemy pieces on those squares
        targets = []
        for attacked_sq in attacked:
            enemy = board.get(attacked_sq)
            if enemy and enemy.color == enemy_color:
                targets.append((attacked_sq, enemy))
        
        # A fork requires 2+ targets
        if len(targets) >= 2:
            total_value = sum(get_piece_value(t[1]) for t in targets)
            forks.append({
                'forking_piece': str(piece),
                'forking_square': square.name,
                'targets': [(t[0].name, str(t[1]), get_piece_value(t[1])) for t in targets],
                'total_value': total_value,
            })
    
    return forks


def find_fork_squares(board: Board, color: Color) -> List[Dict]:
    """
    Find squares where a piece could move to create a fork.
    
    This is for tactics: where can I put my knight/queen/etc to fork pieces?
    
    Returns list of potential fork opportunities with:
        - square: The potential fork square
        - piece: Which of our pieces could go there
        - targets: What enemy pieces would be forked
    """
    opportunities = []
    enemy_color = color.opposite
    
    # Get all enemy piece locations
    enemy_pieces = board.get_pieces_by_color(enemy_color)
    if len(enemy_pieces) < 2:
        return []
    
    # For each of our pieces that can move (especially knights and queens)
    for our_square, our_piece in board.get_pieces_by_color(color):
        # Get all squares this piece can potentially reach
        # (simplified - not checking if path is clear for sliding pieces)
        potential_squares = get_reachable_squares(board, our_square, our_piece)
        
        for candidate_sq in potential_squares:
            # Skip if occupied by friendly piece
            occupant = board.get(candidate_sq)
            if occupant and occupant.color == color:
                continue
            
            # Simulate piece on this square and see what it attacks
            simulated_attacks = get_attacks_from_square(board, candidate_sq, our_piece)
            
            # Count enemy pieces attacked
            targets = []
            for atk_sq in simulated_attacks:
                target = board.get(atk_sq)
                if target and target.color == enemy_color and atk_sq != candidate_sq:
                    targets.append((atk_sq, target))
            
            if len(targets) >= 2:
                # Check if we can actually get there (not blocked, not suicidal)
                enemy_attackers = get_attackers(board, candidate_sq, by_color=enemy_color)
                is_safe = len(enemy_attackers) == 0 or occupant is not None  # capture might be worth it
                
                total_value = sum(get_piece_value(t[1]) for t in targets)
                opportunities.append({
                    'fork_square': candidate_sq.name,
                    'our_piece': str(our_piece),
                    'from_square': our_square.name,
                    'targets': [(t[0].name, str(t[1]), get_piece_value(t[1])) for t in targets],
                    'total_value': total_value,
                    'is_safe': is_safe,
                    'captures': str(occupant) if occupant else None,
                })
    
    # Sort by value
    opportunities.sort(key=lambda x: x['total_value'], reverse=True)
    return opportunities


def get_reachable_squares(board: Board, from_sq: Square, piece: Piece) -> Set[Square]:
    """Get all squares a piece could potentially move to (simplified)."""
    reachable = set()
    
    if piece.piece_type == PieceType.KNIGHT:
        for offset in KNIGHT_OFFSETS:
            sq_new = from_sq.offset(offset[0], offset[1])
            if sq_new:
                reachable.add(sq_new)
    
    elif piece.piece_type == PieceType.KING:
        for offset in KING_OFFSETS:
            sq_new = from_sq.offset(offset[0], offset[1])
            if sq_new:
                reachable.add(sq_new)
    
    elif piece.piece_type == PieceType.PAWN:
        direction = 1 if piece.color == Color.WHITE else -1
        # Forward moves
        sq_new = from_sq.offset(0, direction)
        if sq_new and board.is_empty(sq_new):
            reachable.add(sq_new)
            # Initial double move
            if (piece.color == Color.WHITE and from_sq.rank == 1) or \
               (piece.color == Color.BLACK and from_sq.rank == 6):
                sq_new2 = from_sq.offset(0, direction * 2)
                if sq_new2 and board.is_empty(sq_new2):
                    reachable.add(sq_new2)
        # Captures
        for file_dir in [-1, 1]:
            sq_cap = from_sq.offset(file_dir, direction)
            if sq_cap:
                target = board.get(sq_cap)
                if target and target.color != piece.color:
                    reachable.add(sq_cap)
    
    else:  # Sliding pieces
        directions = []
        if piece.piece_type in (PieceType.BISHOP, PieceType.QUEEN):
            directions.extend(BISHOP_DIRECTIONS)
        if piece.piece_type in (PieceType.ROOK, PieceType.QUEEN):
            directions.extend(ROOK_DIRECTIONS)
        
        for dx, dy in directions:
            current = from_sq
            while True:
                sq_new = current.offset(dx, dy)
                if sq_new is None:
                    break
                occupant = board.get(sq_new)
                if occupant:
                    if occupant.color != piece.color:
                        reachable.add(sq_new)  # Can capture
                    break
                reachable.add(sq_new)
                current = sq_new
    
    return reachable


def get_attacks_from_square(board: Board, from_sq: Square, piece: Piece) -> Set[Square]:
    """Get all squares a piece would attack from a given square."""
    attacked = set()
    
    if piece.piece_type == PieceType.KNIGHT:
        for offset in KNIGHT_OFFSETS:
            sq_new = from_sq.offset(offset[0], offset[1])
            if sq_new:
                attacked.add(sq_new)
    
    elif piece.piece_type == PieceType.KING:
        for offset in KING_OFFSETS:
            sq_new = from_sq.offset(offset[0], offset[1])
            if sq_new:
                attacked.add(sq_new)
    
    elif piece.piece_type == PieceType.PAWN:
        direction = 1 if piece.color == Color.WHITE else -1
        for file_dir in [-1, 1]:
            sq_new = from_sq.offset(file_dir, direction)
            if sq_new:
                attacked.add(sq_new)
    
    else:  # Sliding pieces
        directions = []
        if piece.piece_type in (PieceType.BISHOP, PieceType.QUEEN):
            directions.extend(BISHOP_DIRECTIONS)
        if piece.piece_type in (PieceType.ROOK, PieceType.QUEEN):
            directions.extend(ROOK_DIRECTIONS)
        
        for dx, dy in directions:
            current = from_sq
            while True:
                sq_new = current.offset(dx, dy)
                if sq_new is None:
                    break
                attacked.add(sq_new)
                if board.get(sq_new):  # Blocked (but we still attack this square)
                    break
                current = sq_new
    
    return attacked


# =============================================================================
# PINS - A piece that can't move because it would expose a more valuable piece
# =============================================================================

def find_pins(board: Board, color: Color) -> List[Dict]:
    """
    Find all pinned pieces of the given color.
    
    A pin occurs when a piece can't move (or has limited movement)
    because doing so would expose a more valuable piece behind it.
    
    Returns list of dicts with:
        - pinned_piece: The piece that's pinned
        - pinned_square: Where it sits
        - pinning_piece: The attacker creating the pin
        - pinning_square: Where the pinner sits
        - protected_piece: The valuable piece behind (usually king or queen)
        - protected_square: Where the protected piece sits
        - pin_line: The direction of the pin (diagonal/orthogonal)
    """
    pins = []
    enemy_color = color.opposite
    
    # For each of our valuable pieces (especially king), check for pins
    for protected_sq, protected_piece in board.get_pieces_by_color(color):
        if protected_piece.piece_type not in (PieceType.KING, PieceType.QUEEN, PieceType.ROOK):
            continue  # Only check pins protecting high-value pieces
        
        # Check all 8 directions for potential pins
        all_directions = BISHOP_DIRECTIONS + ROOK_DIRECTIONS
        
        for dx, dy in all_directions:
            # Find first piece in this direction
            first_piece = None
            first_square = None
            second_piece = None
            second_square = None
            
            current = protected_sq
            while True:
                current = current.offset(dx, dy)
                if current is None:
                    break
                
                piece = board.get(current)
                if piece:
                    if first_piece is None:
                        first_piece = piece
                        first_square = current
                    else:
                        second_piece = piece
                        second_square = current
                        break
            
            # For a pin: first piece must be ours, second must be enemy slider
            if first_piece and second_piece:
                if first_piece.color == color and second_piece.color == enemy_color:
                    # Check if the second piece can actually pin along this line
                    is_diagonal = abs(dx) == abs(dy)
                    can_pin = False
                    
                    if is_diagonal:
                        can_pin = second_piece.piece_type in (PieceType.BISHOP, PieceType.QUEEN)
                    else:
                        can_pin = second_piece.piece_type in (PieceType.ROOK, PieceType.QUEEN)
                    
                    if can_pin:
                        pin_type = "diagonal" if is_diagonal else "orthogonal"
                        pins.append({
                            'pinned_piece': str(first_piece),
                            'pinned_square': first_square.name,
                            'pinned_value': get_piece_value(first_piece),
                            'pinning_piece': str(second_piece),
                            'pinning_square': second_square.name,
                            'protected_piece': str(protected_piece),
                            'protected_square': protected_sq.name,
                            'protected_value': get_piece_value(protected_piece),
                            'pin_type': pin_type,
                            'is_absolute': protected_piece.piece_type == PieceType.KING,  # Illegal to break
                        })
    
    return pins


# =============================================================================
# SKEWERS - Like a reverse pin: attack valuable piece, lesser piece behind
# =============================================================================

def find_skewers(board: Board, color: Color) -> List[Dict]:
    """
    Find all potential skewers for the given color.
    
    A skewer is when we attack a valuable piece, and when it moves,
    we can capture a less valuable piece behind it.
    
    Returns list of dicts with:
        - attacking_piece: Our piece doing the skewer
        - attacking_square: Where it sits
        - front_target: The valuable piece being attacked
        - front_square: Where it sits
        - back_target: The piece behind that we'll capture
        - back_square: Where it sits
    """
    skewers = []
    enemy_color = color.opposite
    
    # Find our sliding pieces that could create skewers
    for our_sq, our_piece in board.get_pieces_by_color(color):
        if our_piece.piece_type not in (PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN):
            continue
        
        # Determine valid directions for this piece
        directions = []
        if our_piece.piece_type in (PieceType.BISHOP, PieceType.QUEEN):
            directions.extend(BISHOP_DIRECTIONS)
        if our_piece.piece_type in (PieceType.ROOK, PieceType.QUEEN):
            directions.extend(ROOK_DIRECTIONS)
        
        for dx, dy in directions:
            first_piece = None
            first_square = None
            second_piece = None
            second_square = None
            
            current = our_sq
            while True:
                current = current.offset(dx, dy)
                if current is None:
                    break
                
                piece = board.get(current)
                if piece:
                    if first_piece is None:
                        first_piece = piece
                        first_square = current
                    else:
                        second_piece = piece
                        second_square = current
                        break
            
            # For a skewer: both pieces must be enemy, front > back in value
            if first_piece and second_piece:
                if first_piece.color == enemy_color and second_piece.color == enemy_color:
                    front_value = get_piece_value(first_piece)
                    back_value = get_piece_value(second_piece)
                    
                    if front_value > back_value:
                        skewers.append({
                            'attacking_piece': str(our_piece),
                            'attacking_square': our_sq.name,
                            'front_target': str(first_piece),
                            'front_square': first_square.name,
                            'front_value': front_value,
                            'back_target': str(second_piece),
                            'back_square': second_square.name,
                            'back_value': back_value,
                        })
    
    return skewers


# =============================================================================
# DISCOVERED ATTACKS - Moving a piece reveals an attack from another
# =============================================================================

def find_discoveries(board: Board, color: Color) -> List[Dict]:
    """
    Find potential discovered attack opportunities.
    
    A discovered attack occurs when moving one piece reveals an attack
    from a piece behind it.
    
    Returns list of dicts with:
        - blocking_piece: The piece that could move
        - blocking_square: Where it currently sits
        - hidden_attacker: The piece that would be revealed
        - hidden_square: Where it sits  
        - target: What would be attacked after the discovery
        - target_square: Where the target sits
    """
    discoveries = []
    enemy_color = color.opposite
    
    # Find our sliding pieces
    for slider_sq, slider in board.get_pieces_by_color(color):
        if slider.piece_type not in (PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN):
            continue
        
        # Determine valid directions
        directions = []
        if slider.piece_type in (PieceType.BISHOP, PieceType.QUEEN):
            directions.extend(BISHOP_DIRECTIONS)
        if slider.piece_type in (PieceType.ROOK, PieceType.QUEEN):
            directions.extend(ROOK_DIRECTIONS)
        
        for dx, dy in directions:
            # Look for pattern: slider -> our piece -> empty -> enemy piece
            current = slider_sq
            blocking_piece = None
            blocking_square = None
            target_piece = None
            target_square = None
            
            while True:
                current = current.offset(dx, dy)
                if current is None:
                    break
                
                piece = board.get(current)
                if piece:
                    if blocking_piece is None:
                        # First piece encountered
                        if piece.color == color:
                            blocking_piece = piece
                            blocking_square = current
                        else:
                            # Enemy piece directly in front - no discovery possible
                            break
                    else:
                        # Second piece encountered
                        if piece.color == enemy_color:
                            target_piece = piece
                            target_square = current
                        break
            
            if blocking_piece and target_piece:
                # We have a discovery opportunity!
                # The blocking piece can move anywhere (perpendicular ideally) to reveal attack
                discoveries.append({
                    'hidden_attacker': str(slider),
                    'hidden_square': slider_sq.name,
                    'blocking_piece': str(blocking_piece),
                    'blocking_square': blocking_square.name,
                    'target': str(target_piece),
                    'target_square': target_square.name,
                    'target_value': get_piece_value(target_piece),
                    'is_check': target_piece.piece_type == PieceType.KING,
                })
    
    return discoveries


# =============================================================================
# ALL TACTICS SUMMARY
# =============================================================================

def analyze_tactics(board: Board, color: Color) -> Dict:
    """
    Complete tactical analysis for a position.
    
    Returns dict with all tactical patterns found.
    """
    return {
        'color': 'White' if color == Color.WHITE else 'Black',
        'current_forks': find_forks(board, color),
        'fork_opportunities': find_fork_squares(board, color)[:5],  # Top 5
        'pins_on_us': find_pins(board, color),  # Our pieces pinned
        'pins_on_enemy': find_pins(board, color.opposite),  # Enemy pieces pinned
        'our_skewers': find_skewers(board, color),
        'discovered_attacks': find_discoveries(board, color),
    }


def tactics_summary(board: Board, color: Color) -> str:
    """Human-readable tactics summary."""
    analysis = analyze_tactics(board, color)
    color_name = analysis['color']
    lines = [f"=== Tactical Analysis for {color_name} ===\n"]
    
    # Current forks
    if analysis['current_forks']:
        lines.append("🍴 ACTIVE FORKS:")
        for fork in analysis['current_forks']:
            targets_str = ", ".join([f"{t[1]} on {t[0]}" for t in fork['targets']])
            lines.append(f"  {fork['forking_piece']} on {fork['forking_square']} forks: {targets_str}")
    
    # Fork opportunities
    if analysis['fork_opportunities']:
        lines.append("\n🎯 FORK OPPORTUNITIES:")
        for opp in analysis['fork_opportunities'][:3]:
            targets_str = ", ".join([f"{t[1]} on {t[0]}" for t in opp['targets']])
            safe_str = "✓ safe" if opp['is_safe'] else "⚠️ risky"
            cap_str = f" (captures {opp['captures']})" if opp['captures'] else ""
            lines.append(f"  {opp['our_piece']} to {opp['fork_square']}{cap_str} forks: {targets_str} [{safe_str}]")
    
    # Pins on us
    if analysis['pins_on_us']:
        lines.append("\n📌 WE ARE PINNED:")
        for pin in analysis['pins_on_us']:
            abs_str = " [ABSOLUTE - illegal to break]" if pin['is_absolute'] else ""
            lines.append(f"  {pin['pinned_piece']} on {pin['pinned_square']} pinned by {pin['pinning_piece']} on {pin['pinning_square']}{abs_str}")
    
    # Pins on enemy
    if analysis['pins_on_enemy']:
        lines.append("\n📌 ENEMY IS PINNED:")
        for pin in analysis['pins_on_enemy']:
            abs_str = " [ABSOLUTE]" if pin['is_absolute'] else ""
            lines.append(f"  {pin['pinned_piece']} on {pin['pinned_square']} pinned by {pin['pinning_piece']}{abs_str}")
    
    # Skewers
    if analysis['our_skewers']:
        lines.append("\n⚔️ OUR SKEWERS:")
        for skewer in analysis['our_skewers']:
            lines.append(f"  {skewer['attacking_piece']} on {skewer['attacking_square']} skewers {skewer['front_target']}/{skewer['back_target']}")
    
    # Discovered attacks
    if analysis['discovered_attacks']:
        lines.append("\n💥 DISCOVERED ATTACK OPPORTUNITIES:")
        for disc in analysis['discovered_attacks']:
            check_str = " (DISCOVERED CHECK!)" if disc['is_check'] else ""
            lines.append(f"  Move {disc['blocking_piece']} from {disc['blocking_square']} to reveal {disc['hidden_attacker']} → {disc['target']} on {disc['target_square']}{check_str}")
    
    if not any([analysis['current_forks'], analysis['fork_opportunities'], 
                analysis['pins_on_us'], analysis['pins_on_enemy'],
                analysis['our_skewers'], analysis['discovered_attacks']]):
        lines.append("No major tactical patterns found.")
    
    return "\n".join(lines)


if __name__ == "__main__":
    from board import Board
    
    print("=== Tactics Module Tests ===\n")
    
    # Position with tactical possibilities
    # White has a knight that can fork king and queen
    fen = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
    board = Board.from_fen(fen)
    print(board)
    print()
    
    print(tactics_summary(board, Color.WHITE))
    print("\n" + "="*50 + "\n")
    print(tactics_summary(board, Color.BLACK))
    
    # Test a position with pins
    print("\n\n=== Pin Test Position ===\n")
    # Black knight on f6 is pinned to the king by a bishop on b5... no wait let's make a clear pin
    # Rook on e1 pins knight on e5 to king on e8
    pin_fen = "4k3/8/8/4n3/8/8/8/4R2K w - - 0 1"
    pin_board = Board.from_fen(pin_fen)
    print(pin_board)
    print()
    print(tactics_summary(pin_board, Color.WHITE))
