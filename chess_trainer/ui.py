import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import chess

from .session import DrillSession


SIZE = 68
MARGIN = 22
LIGHT = "#eee8d5"
DARK = "#779467"
HIGHLIGHT = "#e9c46a"
PIECES = {
    (chess.WHITE, chess.KING): "♔",
    (chess.WHITE, chess.QUEEN): "♕",
    (chess.WHITE, chess.ROOK): "♖",
    (chess.WHITE, chess.BISHOP): "♗",
    (chess.WHITE, chess.KNIGHT): "♘",
    (chess.WHITE, chess.PAWN): "♙",
    (chess.BLACK, chess.KING): "♚",
    (chess.BLACK, chess.QUEEN): "♛",
    (chess.BLACK, chess.ROOK): "♜",
    (chess.BLACK, chess.BISHOP): "♝",
    (chess.BLACK, chess.KNIGHT): "♞",
    (chess.BLACK, chess.PAWN): "♟",
}


class TrainerWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chess Endgame Trainer")
        self.root.geometry("1020x690")
        self.root.minsize(850, 620)
        self.session = DrillSession()
        self.events = queue.Queue()
        self.busy = False
        self.closing = False
        self.drag_from = None
        self.drag_point = None
        self.drag_targets = set()
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._refresh()
        self.root.after(60, self._poll)

    def _build(self):
        style = ttk.Style(self.root)
        style.configure("Treeview", rowheight=27, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        body = ttk.Frame(self.root, padding=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        board_size = SIZE * 8 + MARGIN * 2
        self.canvas = tk.Canvas(
            body,
            width=board_size,
            height=board_size,
            bg="#20252b",
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="n", padx=(0, 20))
        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._drag_end)

        panel = ttk.Frame(body)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(4, weight=1)

        ttk.Label(panel, text="Chess Endgame Trainer", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self.category = tk.StringVar()
        self.details = tk.StringVar()
        self.status = tk.StringVar()
        ttk.Label(panel, textvariable=self.category, wraplength=370, font=("Segoe UI", 12, "bold")).grid(
            row=1, column=0, sticky="w", pady=(0, 6)
        )
        ttk.Label(panel, textvariable=self.details, wraplength=370).grid(
            row=2, column=0, sticky="w", pady=(0, 10)
        )

        controls = ttk.Frame(panel)
        controls.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.new_button = ttk.Button(controls, text="New drill", command=self._new_drill)
        self.new_button.pack(side="left")
        self.resign_button = ttk.Button(controls, text="Resign", command=self._resign)
        self.resign_button.pack(side="left", padx=8)

        self.moves = ttk.Treeview(
            panel,
            columns=("move", "accuracy", "surprisal", "entropy", "fluency"),
            show="headings",
            height=10,
        )
        for key, title, width in (
            ("move", "Move", 62),
            ("accuracy", "Accuracy", 80),
            ("surprisal", "I* bits", 72),
            ("entropy", "H bits", 72),
            ("fluency", "Fluency", 72),
        ):
            self.moves.heading(key, text=title)
            self.moves.column(key, width=width, anchor="center")
        self.moves.grid(row=4, column=0, sticky="nsew")

        entry_row = ttk.Frame(panel)
        entry_row.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        entry_row.columnconfigure(0, weight=1)
        self.move_text = tk.StringVar()
        self.entry = ttk.Entry(entry_row, textvariable=self.move_text)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Return>", lambda _event: self._submit_move())
        self.play_button = ttk.Button(entry_row, text="Play", command=self._submit_move)
        self.play_button.grid(row=0, column=1, padx=(8, 0))
        self.status_label = ttk.Label(panel, textvariable=self.status, wraplength=370)
        self.status_label.grid(row=6, column=0, sticky="w", pady=(12, 0))

    def _square_at(self, x, y):
        col = int((x - MARGIN) // SIZE)
        row = int((y - MARGIN) // SIZE)
        if not (0 <= col < 8 and 0 <= row < 8):
            return None
        if self.session.user_color == chess.WHITE:
            file_index, rank_index = col, 7 - row
        else:
            file_index, rank_index = 7 - col, row
        return chess.square(file_index, rank_index)

    def _coordinates(self, square):
        file_index, rank_index = chess.square_file(square), chess.square_rank(square)
        if self.session.user_color == chess.WHITE:
            return file_index, 7 - rank_index
        return 7 - file_index, rank_index

    def _draw_board(self, dragging=False):
        self.canvas.delete("all")
        for row in range(8):
            for col in range(8):
                square = self._square_at(MARGIN + col * SIZE + 1, MARGIN + row * SIZE + 1)
                color = HIGHLIGHT if square in self.drag_targets else (
                    LIGHT if (row + col) % 2 == 0 else DARK
                )
                x1, y1 = MARGIN + col * SIZE, MARGIN + row * SIZE
                self.canvas.create_rectangle(
                    x1, y1, x1 + SIZE, y1 + SIZE, fill=color, outline=color
                )
                piece = self.session.board.piece_at(square)
                if piece and not (dragging and square == self.drag_from):
                    self.canvas.create_text(
                        x1 + SIZE / 2,
                        y1 + SIZE / 2,
                        text=PIECES[(piece.color, piece.piece_type)],
                        fill="#f8f8f8" if piece.color else "#20252b",
                        font=("Segoe UI Symbol", 46),
                    )

        if dragging and self.drag_from is not None and self.drag_point:
            piece = self.session.board.piece_at(self.drag_from)
            if piece:
                self.canvas.create_text(
                    *self.drag_point,
                    text=PIECES[(piece.color, piece.piece_type)],
                    fill="#f8f8f8" if piece.color else "#20252b",
                    font=("Segoe UI Symbol", 46),
                )

        for index in range(8):
            file_index = index if self.session.user_color == chess.WHITE else 7 - index
            rank_index = 7 - index if self.session.user_color == chess.WHITE else index
            self.canvas.create_text(
                MARGIN + index * SIZE + 7,
                MARGIN + 8 * SIZE - 7,
                text=chess.FILE_NAMES[file_index],
                fill="#20252b",
                anchor="sw",
                font=("Segoe UI", 8, "bold"),
            )
            self.canvas.create_text(
                MARGIN + 7,
                MARGIN + index * SIZE + 7,
                text=str(8 - index if self.session.user_color == chess.WHITE else index + 1),
                fill="#20252b",
                anchor="nw",
                font=("Segoe UI", 8, "bold"),
            )

    def _drag_start(self, event):
        if self.busy or not self.session.active or self.session.board.turn != self.session.user_color:
            return
        square = self._square_at(event.x, event.y)
        piece = self.session.board.piece_at(square) if square is not None else None
        if piece is None or piece.color != self.session.user_color:
            return
        self.drag_from = square
        self.drag_point = (event.x, event.y)
        self.drag_targets = {
            move.to_square
            for move in self.session.board.legal_moves
            if move.from_square == square
        }
        self._draw_board(dragging=True)

    def _drag_motion(self, event):
        if self.drag_from is not None:
            self.drag_point = (event.x, event.y)
            self._draw_board(dragging=True)

    def _drag_end(self, event):
        if self.drag_from is None:
            return
        source, target = self.drag_from, self._square_at(event.x, event.y)
        self.drag_from = self.drag_point = None
        self.drag_targets.clear()
        self._draw_board()
        if target is None:
            return
        moves = [
            move for move in self.session.board.legal_moves
            if move.from_square == source and move.to_square == target
        ]
        if moves:
            move = next((move for move in moves if move.promotion == chess.QUEEN), moves[0])
            self.move_text.set(move.uci())
            self._submit_move()

    def _new_drill(self):
        self.session.start_drill()
        self._refresh()

    def _resign(self):
        try:
            self.session.resign()
        except Exception as error:
            messagebox.showerror("Could not save result", str(error), parent=self.root)
        self._refresh()

    def _submit_move(self):
        if self.busy or not self.session.active:
            return
        text = self.move_text.get().strip()
        if not text:
            return
        self.busy = True
        self.status.set("Analyzing position…")
        self._controls()
        threading.Thread(target=self._play_in_background, args=(text,), daemon=True).start()

    def _play_in_background(self, text):
        try:
            self.session.play_move(text)
        except Exception as error:
            self.events.put(error)
        else:
            self.events.put(None)

    def _poll(self):
        if self.busy:
            try:
                error = self.events.get_nowait()
            except queue.Empty:
                pass
            else:
                self.busy = False
                self.move_text.set("")
                if error is not None:
                    messagebox.showerror("Move failed", str(error), parent=self.root)
                self._refresh()
        if self.closing and not self.busy:
            self._destroy()
            return
        self.root.after(60, self._poll)

    def _controls(self):
        state = "disabled" if self.busy else "normal"
        self.new_button.configure(state=state)
        self.resign_button.configure(
            state="normal" if self.session.active and not self.busy else "disabled"
        )
        self.entry.configure(
            state="normal" if self.session.active and not self.busy else "disabled"
        )
        self.play_button.configure(
            state="normal" if self.session.active and not self.busy else "disabled"
        )

    def _refresh(self):
        self._draw_board()
        self.category.set(self.session.category)
        stat = self.session.stats[self.session.category]
        lower = stat["mu"] - 1.96 * stat["phi"]
        opponent = "Maia-3" if lower < 2450 else "Stockfish (depth 18)"
        self.details.set(
            f"Glicko-2 μ {stat['mu']:.0f} · RD {stat['phi']:.0f} · "
            f"{opponent} (lower bound {lower:.0f})"
        )
        result = {1.0: "Win", 0.5: "Draw", 0.0: "Loss"}.get(self.session.result)
        self.status.set(
            "Drag a piece or enter SAN/UCI." if self.session.active
            else f"Drill complete — {result}" if result
            else "Choose New drill to begin."
        )
        for item in self.moves.get_children():
            self.moves.delete(item)
        for row in self.session.rows:
            self.moves.insert(
                "",
                "end",
                values=(
                    row["move"],
                    f"{row['accuracy']:.1f}%",
                    f"{row['surprisal']:.2f}",
                    f"{row['entropy']:.2f}",
                    f"{row['fluency']:.2f}",
                ),
            )
        self._controls()

    def _close(self):
        self.closing = True
        if not self.busy:
            self._destroy()

    def _destroy(self):
        try:
            self.session.engines.close()
        except Exception as error:
            messagebox.showerror("Engine shutdown", str(error), parent=self.root)
        finally:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


def run():
    TrainerWindow().run()
