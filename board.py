"""
Chess Board Representation
Core data structures for parsing FEN and querying board state.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import Enum


class Color(Enum):
    WHITE = 'w'
    BLACK = 'b'
    
    @property
    def opposite(self):
        return Color.BLACK if self == Color.WHITE else Color.WHITE


class PieceType(Enum):
    PAWN = 'p'
    KNIGHT = 'n'
    BISHOP = 'b'
    ROOK = 'r'
    QUEEN = 'q'
    KING = 'k'


@dataclass
class Piece:
    piece_type: PieceType
    color: Color
    
    def __str__(self):
        char = self.piece_type.value
        return char.upper() if self.color == Color.WHITE else char
    
    @classmethod
    def from_char(cls, char: str) -> 'Piece':
        """Create a Piece from FEN character (K=white king, k=black king, etc.)"""
        color = Color.WHITE if char.isupper() else Color.BLACK
        piece_type = PieceType(char.lower())
        return cls(piece_type, color)


@dataclass
class Square:
    """Represents a square on the board (0-63 or file/rank)"""
    index: int  # 0-63, where 0=a1, 7=h1, 56=a8, 63=h8
    
    @classmethod
    def from_algebraic(cls, name: str) -> 'Square':
        """Convert 'e4' to Square"""
        file = ord(name[0].lower()) - ord('a')  # 0-7
        rank = int(name[1]) - 1  # 0-7
        return cls(rank * 8 + file)
    
    @property
    def file(self) -> int:
        """0-7 (a-h)"""
        return self.index % 8
    
    @property
    def rank(self) -> int:
        """0-7 (1-8)"""
        return self.index // 8
    
    @property
    def file_char(self) -> str:
        return chr(ord('a') + self.file)
    
    @property
    def rank_char(self) -> str:
        return str(self.rank + 1)
    
    @property
    def name(self) -> str:
        return f"{self.file_char}{self.rank_char}"
    
    def __str__(self):
        return self.name
    
    def __hash__(self):
        return hash(self.index)
    
    def __eq__(self, other):
        if isinstance(other, Square):
            return self.index == other.index
        return False
    
    def offset(self, file_delta: int, rank_delta: int) -> Optional['Square']:
        """Get square offset by (file, rank). Returns None if off board."""
        new_file = self.file + file_delta
        new_rank = self.rank + rank_delta
        if 0 <= new_file <= 7 and 0 <= new_rank <= 7:
            return Square(new_rank * 8 + new_file)
        return None


class Board:
    """
    Chess board representation.
    Stores pieces and provides query methods.
    """
    
    def __init__(self):
        self.pieces: Dict[int, Piece] = {}  # square index -> piece
        self.turn: Color = Color.WHITE
        self.castling_rights: str = "KQkq"
        self.en_passant: Optional[Square] = None
        self.halfmove_clock: int = 0
        self.fullmove_number: int = 1
    
    @classmethod
    def from_fen(cls, fen: str) -> 'Board':
        """Parse a FEN string into a Board."""
        board = cls()
        parts = fen.split()
        
        # Parse piece placement
        piece_placement = parts[0]
        rank = 7  # Start from rank 8 (index 7)
        file = 0
        
        for char in piece_placement:
            if char == '/':
                rank -= 1
                file = 0
            elif char.isdigit():
                file += int(char)
            else:
                square_idx = rank * 8 + file
                board.pieces[square_idx] = Piece.from_char(char)
                file += 1
        
        # Parse active color
        if len(parts) > 1:
            board.turn = Color.WHITE if parts[1] == 'w' else Color.BLACK
        
        # Parse castling rights
        if len(parts) > 2:
            board.castling_rights = parts[2] if parts[2] != '-' else ""
        
        # Parse en passant square
        if len(parts) > 3 and parts[3] != '-':
            board.en_passant = Square.from_algebraic(parts[3])
        
        # Parse halfmove clock
        if len(parts) > 4:
            board.halfmove_clock = int(parts[4])
        
        # Parse fullmove number
        if len(parts) > 5:
            board.fullmove_number = int(parts[5])
        
        return board
    
    @classmethod
    def starting_position(cls) -> 'Board':
        """Return a board set up in the standard starting position."""
        return cls.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    
    def get(self, square: Square) -> Optional[Piece]:
        """Get the piece on a square, or None if empty."""
        return self.pieces.get(square.index)
    
    def set(self, square: Square, piece: Optional[Piece]):
        """Set or clear a piece on a square."""
        if piece is None:
            self.pieces.pop(square.index, None)
        else:
            self.pieces[square.index] = piece
    
    def is_empty(self, square: Square) -> bool:
        """Check if a square is empty."""
        return square.index not in self.pieces
    
    def get_pieces_by_color(self, color: Color) -> List[Tuple[Square, Piece]]:
        """Get all pieces of a given color."""
        return [
            (Square(idx), piece) 
            for idx, piece in self.pieces.items() 
            if piece.color == color
        ]
    
    def get_pieces_by_type(self, piece_type: PieceType, color: Optional[Color] = None) -> List[Tuple[Square, Piece]]:
        """Get all pieces of a given type (optionally filtered by color)."""
        results = []
        for idx, piece in self.pieces.items():
            if piece.piece_type == piece_type:
                if color is None or piece.color == color:
                    results.append((Square(idx), piece))
        return results
    
    def find_king(self, color: Color) -> Optional[Square]:
        """Find the king of the given color."""
        kings = self.get_pieces_by_type(PieceType.KING, color)
        return kings[0][0] if kings else None
    
    def to_fen(self) -> str:
        """Convert board to FEN string."""
        rows = []
        for rank in range(7, -1, -1):  # 8 down to 1
            row = ""
            empty_count = 0
            for file in range(8):
                square_idx = rank * 8 + file
                piece = self.pieces.get(square_idx)
                if piece:
                    if empty_count > 0:
                        row += str(empty_count)
                        empty_count = 0
                    row += str(piece)
                else:
                    empty_count += 1
            if empty_count > 0:
                row += str(empty_count)
            rows.append(row)
        
        piece_placement = "/".join(rows)
        turn = self.turn.value
        castling = self.castling_rights if self.castling_rights else "-"
        ep = self.en_passant.name if self.en_passant else "-"
        
        return f"{piece_placement} {turn} {castling} {ep} {self.halfmove_clock} {self.fullmove_number}"
    
    def __str__(self):
        """Pretty print the board."""
        lines = []
        lines.append("  a b c d e f g h")
        lines.append("  ─────────────────")
        for rank in range(7, -1, -1):
            row = f"{rank + 1}│"
            for file in range(8):
                square_idx = rank * 8 + file
                piece = self.pieces.get(square_idx)
                if piece:
                    row += str(piece) + " "
                else:
                    row += ". "
            row += f"│{rank + 1}"
            lines.append(row)
        lines.append("  ─────────────────")
        lines.append("  a b c d e f g h")
        return "\n".join(lines)


# Convenience functions
def sq(name: str) -> Square:
    """Shorthand for Square.from_algebraic('e4')"""
    return Square.from_algebraic(name)


if __name__ == "__main__":
    # Quick test
    board = Board.starting_position()
    print(board)
    print(f"\nFEN: {board.to_fen()}")
    print(f"\nPiece on e2: {board.get(sq('e2'))}")
    print(f"Piece on e4: {board.get(sq('e4'))}")
    print(f"White king at: {board.find_king(Color.WHITE)}")
