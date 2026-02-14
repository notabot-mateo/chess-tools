#!/usr/bin/env python3
"""
Chess Vision CLI - A spatial reasoning prosthetic for AI chess.

Usage:
    python chess_vision.py <fen> analyze <square>
    python chess_vision.py <fen> move <from> <to>
    python chess_vision.py <fen> hanging <color>
    python chess_vision.py <fen> tactics <color>
    python chess_vision.py <fen> board
    python chess_vision.py <fen> all
    
Examples:
    python chess_vision.py "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1" analyze e4
    python chess_vision.py "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2" hanging black
    python chess_vision.py "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4" tactics white
"""

import sys
import json
from board import Board, Square, Color, sq
from attacks import analyze_square, find_hanging_pieces, find_undefended_pieces
from analyze_move import analyze_move, quick_check, check_all_hanging
from tactics import tactics_summary, analyze_tactics


def print_help():
    print(__doc__)


def main():
    if len(sys.argv) < 3:
        print_help()
        return
    
    fen = sys.argv[1]
    command = sys.argv[2].lower()
    
    try:
        board = Board.from_fen(fen)
    except Exception as e:
        print(f"Error parsing FEN: {e}")
        return
    
    if command == "board":
        print(board)
        print(f"\nTurn: {'White' if board.turn == Color.WHITE else 'Black'}")
        
    elif command == "analyze":
        if len(sys.argv) < 4:
            print("Usage: chess_vision.py <fen> analyze <square>")
            return
        square = sq(sys.argv[3])
        result = analyze_square(board, square)
        print(json.dumps(result, indent=2))
        
    elif command == "move":
        if len(sys.argv) < 5:
            print("Usage: chess_vision.py <fen> move <from> <to>")
            return
        from_sq = sq(sys.argv[3])
        to_sq = sq(sys.argv[4])
        
        print(quick_check(board, from_sq, to_sq))
        print("\n--- Full Analysis ---")
        result = analyze_move(board, from_sq, to_sq)
        print(json.dumps(result, indent=2))
        
    elif command == "hanging":
        if len(sys.argv) < 4:
            print("Usage: chess_vision.py <fen> hanging <white|black>")
            return
        color = Color.WHITE if sys.argv[3].lower() == "white" else Color.BLACK
        print(check_all_hanging(board, color))
        
        # Also show undefended pieces
        undefended = find_undefended_pieces(board, color)
        if undefended:
            color_name = 'White' if color == Color.WHITE else 'Black'
            print(f"\nUndefended {color_name} pieces (not necessarily under attack):")
            for sq_obj, piece in undefended:
                print(f"  {piece} on {sq_obj}")
        
    elif command == "tactics":
        if len(sys.argv) < 4:
            print("Usage: chess_vision.py <fen> tactics <white|black>")
            return
        color = Color.WHITE if sys.argv[3].lower() == "white" else Color.BLACK
        print(tactics_summary(board, color))
        
    elif command == "all":
        # Full board analysis
        print(board)
        print()
        print(check_all_hanging(board, Color.WHITE))
        print()
        print(check_all_hanging(board, Color.BLACK))
        print()
        print("="*50)
        print()
        print(tactics_summary(board, board.turn))
        
    else:
        print(f"Unknown command: {command}")
        print_help()


if __name__ == "__main__":
    main()
