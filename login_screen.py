"""
login_screen.py
---------------
Login screen for Kanta's Crypto Alerts.
Shows two big buttons: User Login / Admin Login.
Phone number is the password — no username field.
On success, opens App() or AdminPanel() accordingly.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
from PIL import Image, ImageTk
import io

import db_manager
import auth_manager
from icon_manager import get_app_logo_image, APP_ICON_ICO, APP_ICON_PNG, ROOT_ICON_PNG

# ─────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────
BG_MAIN        = "#0d1117"
BG_PANEL       = "#161b22"
BORDER_COLOR   = "#21262d"
TEXT_PRIMARY   = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
ACCENT_GREEN   = "#3fb950"
ACCENT_BLUE    = "#58a6ff"
ACCENT_RED     = "#f85149"
ACCENT_YELLOW  = "#d29922"
BTN_ADMIN      = "#1f2d1f"
BTN_USER       = "#1a1f2e"


def apply_window_icon(window):
    import os
    try:
        if os.path.exists(APP_ICON_ICO):
            window.iconbitmap(APP_ICON_ICO)
    except Exception:
        pass
    try:
        path = ROOT_ICON_PNG if os.path.exists(ROOT_ICON_PNG) else APP_ICON_PNG
        if os.path.exists(path):
            im = Image.open(path)
            photo = ImageTk.PhotoImage(im)
            window.iconphoto(False, photo)
            window._icon_photo_ref = photo
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════
# LoginScreen
# ═══════════════════════════════════════════════════════════════════════
class LoginScreen(ctk.CTk):
    """
    Main login window.
    Launches before the main App.
    On success: destroys itself and starts App or AdminPanel.
    """

    def __init__(self):
        super().__init__()
        self.title("Kanta's Crypto Alerts — Login · लॉग इन")
        self.geometry("480x560")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)
        apply_window_icon(self)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self._mode = None        # "user" or "admin"
        self._login_in_progress = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ──────────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Top logo + title ────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)
        top.pack(fill="x")

        logo_frame = ctk.CTkFrame(top, fg_color="transparent")
        logo_frame.pack(pady=(20, 6))

        app_logo = get_app_logo_image((52, 52))
        if app_logo:
            ctk.CTkLabel(logo_frame, image=app_logo, text="").pack()

        ctk.CTkLabel(top, text="Kanta's Crypto Alerts",
                     font=ctk.CTkFont("Segoe UI", 22, "bold"),
                     text_color=ACCENT_GREEN).pack(pady=(4, 0))
        ctk.CTkLabel(top, text="कान्ता क्रिप्टो अलर्ट्स",
                     font=ctk.CTkFont("Segoe UI", 12),
                     text_color=TEXT_SECONDARY).pack(pady=(0, 14))

        # ── Mode selector buttons ────────────────────────────────────
        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(pady=(28, 8))

        self._user_btn = ctk.CTkButton(
            mode_frame,
            text="👤  User Login\n     यूज़र लॉगिन",
            width=170, height=72,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            fg_color=BTN_USER,
            hover_color="#22304a",
            text_color=ACCENT_BLUE,
            border_width=2, border_color=ACCENT_BLUE,
            corner_radius=12,
            command=lambda: self._select_mode("user")
        )
        self._user_btn.pack(side="left", padx=14)

        self._admin_btn = ctk.CTkButton(
            mode_frame,
            text="🔐  Admin Login\n      एडमिन लॉगिन",
            width=170, height=72,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            fg_color=BTN_ADMIN,
            hover_color="#1e3a1e",
            text_color=ACCENT_GREEN,
            border_width=2, border_color=ACCENT_GREEN,
            corner_radius=12,
            command=lambda: self._select_mode("admin")
        )
        self._admin_btn.pack(side="left", padx=14)

        # ── Password / phone entry ───────────────────────────────────
        entry_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=12)
        entry_frame.pack(fill="x", padx=40, pady=(20, 8))

        self._entry_label = ctk.CTkLabel(
            entry_frame,
            text="Select login type above",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=TEXT_SECONDARY
        )
        self._entry_label.pack(pady=(14, 4))

        self._phone_entry = ctk.CTkEntry(
            entry_frame,
            width=280, height=44,
            placeholder_text="Enter phone number / फ़ोन नंबर",
            font=ctk.CTkFont("Segoe UI", 14),
            fg_color=BG_MAIN,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
            show="•",
            state="disabled"
        )
        self._phone_entry.pack(pady=(0, 8))
        self._phone_entry.bind("<Return>", lambda e: self._do_login())

        self._login_btn = ctk.CTkButton(
            entry_frame,
            text="Login  ·  लॉग इन  →",
            width=200, height=40,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            fg_color=ACCENT_GREEN,
            hover_color="#2d8f42",
            text_color=BG_MAIN,
            corner_radius=10,
            state="disabled",
            command=self._do_login
        )
        self._login_btn.pack(pady=(0, 14))

        # ── Status label ─────────────────────────────────────────────
        self._status = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TEXT_SECONDARY,
            wraplength=380
        )
        self._status.pack(pady=6)

        # ── Bottom note ──────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Data synced via NeonDB  ·  सभी डेटा सुरक्षित क्लाउड में",
            font=ctk.CTkFont("Segoe UI", 9),
            text_color=TEXT_SECONDARY
        ).pack(side="bottom", pady=14)

    # ──────────────────────────────────────────────────────────────────
    # Mode selection
    # ──────────────────────────────────────────────────────────────────

    def _select_mode(self, mode: str):
        self._mode = mode
        is_admin = (mode == "admin")
        self._user_btn.configure(
            border_color=ACCENT_BLUE if mode == "user" else BORDER_COLOR
        )
        self._admin_btn.configure(
            border_color=ACCENT_GREEN if mode == "admin" else BORDER_COLOR
        )
        self._phone_entry.configure(state="normal")
        self._login_btn.configure(state="normal")

        label = (
            "Admin phone number (password)  /  एडमिन फ़ोन नंबर"
            if is_admin else
            "Your phone number (password)  /  आपका फ़ोन नंबर"
        )
        self._entry_label.configure(text=label)
        self._phone_entry.delete(0, tk.END)
        self._phone_entry.focus_set()
        self._status.configure(text="", text_color=TEXT_SECONDARY)

    # ──────────────────────────────────────────────────────────────────
    # Login logic
    # ──────────────────────────────────────────────────────────────────

    def _do_login(self):
        if self._login_in_progress:
            return
        if not self._mode:
            self._status.configure(
                text="Please select User Login or Admin Login first.\nपहले लॉगिन प्रकार चुनें।",
                text_color=ACCENT_YELLOW
            )
            return

        phone = self._phone_entry.get().strip()
        if not phone:
            self._status.configure(text="Phone number cannot be empty.  /  फ़ोन नंबर खाली है।",
                                   text_color=ACCENT_RED)
            return

        self._login_in_progress = True
        self._login_btn.configure(state="disabled", text="Logging in…")
        self._status.configure(text="Connecting to database…  /  डेटाबेस से कनेक्ट हो रहे हैं…",
                               text_color=TEXT_SECONDARY)

        threading.Thread(target=self._auth_thread, args=(phone,), daemon=True).start()

    def _auth_thread(self, phone: str):
        try:
            user = db_manager.get_user_by_phone(phone)
            self.after(0, lambda: self._handle_auth_result(user, phone))
        except Exception as e:
            self.after(0, lambda: self._handle_error(str(e)))

    def _handle_auth_result(self, user: dict | None, phone: str):
        self._login_in_progress = False
        self._login_btn.configure(state="normal", text="Login  ·  लॉग इन  →")

        if user is None:
            self._status.configure(
                text="Phone number not recognised.  /  फ़ोन नंबर नहीं मिला।",
                text_color=ACCENT_RED
            )
            return

        # Mode check: if admin button clicked, require admin user
        if self._mode == "admin" and not user.get("is_admin"):
            self._status.configure(
                text="This phone number does not have admin access.\nयह फ़ोन नंबर एडमिन नहीं है।",
                text_color=ACCENT_RED
            )
            return

        # Success — create session, save locally, open app
        try:
            token = db_manager.create_session(user["id"])
            db_manager.update_user_last_login(user["id"])
            auth_manager.save_local_session(
                token=token,
                user_id=user["id"],
                is_admin=bool(user.get("is_admin")),
                display_name=user["display_name"]
            )
        except Exception as e:
            print(f"[Login] Session error: {e}")

        self._launch_app(user)

    def _handle_error(self, err: str):
        self._login_in_progress = False
        self._login_btn.configure(state="normal", text="Login  ·  लॉग इन  →")
        self._status.configure(
            text=f"Connection error: {err[:80]}\nडेटाबेस त्रुटि — इंटरनेट जाँचें।",
            text_color=ACCENT_RED
        )

    def _launch_app(self, user: dict):
        """Destroy login screen and open the appropriate window."""
        self.destroy()

        if user.get("is_admin"):
            from admin_panel import AdminPanel
            panel = AdminPanel(user)
            panel.mainloop()
        else:
            from gui import App
            app = App(current_user=user)
            app.mainloop()
