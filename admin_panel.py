"""
admin_panel.py
--------------
Admin panel for Kanta's Crypto Alerts.
Allows admin to:
  - View all users with profile pictures
  - Create new users (name, phone, optional profile pic)
  - Delete users
  - View full alert history for any user
  - Open the main Crypto Alerts app as admin
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import io
from PIL import Image, ImageTk, ImageOps

import db_manager
import auth_manager
from icon_manager import get_app_logo_image, APP_ICON_ICO, APP_ICON_PNG, ROOT_ICON_PNG

# ─────────────────────────────────────────────
BG_MAIN        = "#0d1117"
BG_PANEL       = "#161b22"
BG_ROW         = "#0d1117"
BG_ROW_ALT     = "#111720"
BORDER_COLOR   = "#21262d"
TEXT_PRIMARY   = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
ACCENT_GREEN   = "#3fb950"
ACCENT_RED     = "#f85149"
ACCENT_BLUE    = "#58a6ff"
ACCENT_YELLOW  = "#d29922"
BTN_DEFAULT    = "#21262d"
# ─────────────────────────────────────────────


def apply_window_icon(window):
    import os
    try:
        if os.path.exists(APP_ICON_ICO):
            window.iconbitmap(APP_ICON_ICO)
    except Exception:
        pass
    try:
        import os
        path = ROOT_ICON_PNG if os.path.exists(ROOT_ICON_PNG) else APP_ICON_PNG
        if os.path.exists(path):
            im = Image.open(path)
            photo = ImageTk.PhotoImage(im)
            window.iconphoto(False, photo)
            window._icon_photo_ref = photo
    except Exception:
        pass


def make_circle_image(img: Image.Image, size: int) -> ctk.CTkImage:
    """Crop image to a circle, return CTkImage."""
    img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    import PIL.ImageDraw as ImageDraw
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return ctk.CTkImage(img, size=(size, size))


def load_profile_pic(pic_bytes: bytes | None, size: int = 42) -> ctk.CTkImage | None:
    """Load profile pic bytes into a round CTkImage, or None."""
    if not pic_bytes:
        return None
    try:
        img = Image.open(io.BytesIO(bytes(pic_bytes)))
        return make_circle_image(img, size)
    except Exception:
        return None



# ═══════════════════════════════════════════════════════════════════════
# EditUserDialog
# ═══════════════════════════════════════════════════════════════════════
class EditUserDialog(ctk.CTkToplevel):
    """
    Modal dialog for editing a user's details:
    - Display Name (पूरा नाम)
    - Phone / Password (फ़ोन नंबर / पासवर्ड)
    - Profile Picture (📷 Change / ❌ Remove)
    """

    def __init__(self, parent, user: dict, on_saved=None):
        super().__init__(parent)
        self.parent = parent
        self.user = dict(user)
        self.on_saved = on_saved

        self.title(f"Edit User · {self.user.get('display_name', 'User')}")
        self.geometry("460x540")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)
        apply_window_icon(self)

        self.transient(parent)
        self.grab_set()

        self._selected_pic_bytes: bytes | None = None
        self._clear_pic = False
        self._is_saving = False

        self._build_ui()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        try:
            px = self.parent.winfo_x()
            py = self.parent.winfo_y()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            x = px + max(0, (pw - 460) // 2)
            y = py + max(0, (ph - 540) // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)
        hdr.pack(fill="x")

        is_admin = self.user.get("is_admin", False)
        title_text = f"✏️  Edit {'Admin' if is_admin else 'User'}  ·  संपादित करें"
        ctk.CTkLabel(
            hdr, text=title_text,
            font=ctk.CTkFont("Segoe UI", 15, "bold"),
            text_color=ACCENT_GREEN if is_admin else ACCENT_BLUE
        ).pack(padx=16, pady=(12, 2), anchor="w")

        ctk.CTkLabel(
            hdr,
            text=f"User ID: #{self.user.get('id')}  |  {self.user.get('display_name', '')}",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=TEXT_SECONDARY
        ).pack(padx=16, pady=(0, 10), anchor="w")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)

        # Avatar card
        avatar_frame = ctk.CTkFrame(body, fg_color=BG_PANEL, corner_radius=10)
        avatar_frame.pack(fill="x", pady=(0, 12), padx=2)

        avatar_inner = ctk.CTkFrame(avatar_frame, fg_color="transparent")
        avatar_inner.pack(padx=12, pady=10, fill="x")

        self._preview_label = ctk.CTkLabel(avatar_inner, text="", width=54, height=54)
        self._preview_label.pack(side="left", padx=(0, 14))

        self._refresh_avatar_preview()

        btn_box = ctk.CTkFrame(avatar_inner, fg_color="transparent")
        btn_box.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            btn_box, text="📷 Change Photo",
            width=130, height=30,
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color=BTN_DEFAULT, hover_color="#30363d",
            text_color=ACCENT_BLUE,
            command=self._pick_photo
        ).pack(anchor="w", pady=(0, 4))

        ctk.CTkButton(
            btn_box, text="❌ Remove Photo",
            width=130, height=26,
            font=ctk.CTkFont("Segoe UI", 10),
            fg_color="transparent", hover_color="#3d0f14",
            text_color=ACCENT_RED,
            command=self._remove_photo
        ).pack(anchor="w")

        # Name entry
        ctk.CTkLabel(
            body, text="Full Name  ·  पूरा नाम:",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=4, pady=(4, 2))

        self._name_entry = ctk.CTkEntry(
            body, height=38,
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG_PANEL, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self._name_entry.pack(fill="x", padx=2, pady=(0, 10))
        self._name_entry.insert(0, self.user.get("display_name", ""))

        # Phone / Password entry
        ctk.CTkLabel(
            body, text="Phone Number / Password  ·  फ़ोन नंबर (पासवर्ड):",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=4, pady=(4, 2))

        self._phone_entry = ctk.CTkEntry(
            body, height=38,
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG_PANEL, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self._phone_entry.pack(fill="x", padx=2, pady=(0, 4))
        self._phone_entry.insert(0, self.user.get("phone", ""))

        ctk.CTkLabel(
            body,
            text="ℹ️ This phone number is used as the login password.  /  यह नंबर लॉगिन पासवर्ड है।",
            font=ctk.CTkFont("Segoe UI", 9),
            text_color=TEXT_SECONDARY
        ).pack(anchor="w", padx=4, pady=(0, 10))

        # Status message
        self._status_label = ctk.CTkLabel(
            body, text="",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=TEXT_SECONDARY,
            wraplength=390
        )
        self._status_label.pack(pady=4)

        # Action buttons
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))

        self._save_btn = ctk.CTkButton(
            btn_row, text="💾 Save Changes  ·  सहेजें",
            height=38,
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=ACCENT_GREEN, hover_color="#2d8f42",
            text_color=BG_MAIN,
            command=self._save
        )
        self._save_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Cancel  ·  रद्द करें",
            height=38, width=105,
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color=BTN_DEFAULT, hover_color="#30363d",
            text_color=TEXT_SECONDARY,
            command=self.destroy
        ).pack(side="right")

    def _refresh_avatar_preview(self):
        if self._selected_pic_bytes:
            img = load_profile_pic(self._selected_pic_bytes, 50)
            if img:
                self._preview_label.configure(image=img, text="", fg_color="transparent")
                return
        elif not self._clear_pic:
            pic_bytes = self.user.get("profile_pic")
            if not pic_bytes:
                try:
                    full_u = db_manager.get_user_by_id(self.user["id"])
                    if full_u and full_u.get("profile_pic"):
                        pic_bytes = full_u["profile_pic"]
                        self.user["profile_pic"] = pic_bytes
                except Exception:
                    pass
            if pic_bytes:
                img = load_profile_pic(pic_bytes, 50)
                if img:
                    self._preview_label.configure(image=img, text="", fg_color="transparent")
                    return

        name = self._name_entry.get().strip() if hasattr(self, "_name_entry") else self.user.get("display_name", "?")
        letter = (name[0].upper() if name else "?")
        self._preview_label.configure(
            image=None,
            text=letter,
            font=ctk.CTkFont("Segoe UI", 18, "bold"),
            text_color=BG_MAIN,
            fg_color=ACCENT_BLUE,
            corner_radius=25
        )

    def _pick_photo(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Profile Photo / प्रोफ़ाइल फ़ोटो चुनें",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            img = Image.open(path)
            img.thumbnail((400, 400), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            self._selected_pic_bytes = buf.getvalue()
            self._clear_pic = False
            self._refresh_avatar_preview()
            self._status_label.configure(text="New photo selected ✓", text_color=ACCENT_GREEN)
        except Exception as e:
            self._status_label.configure(text=f"Image error: {e}", text_color=ACCENT_RED)

    def _remove_photo(self):
        self._selected_pic_bytes = None
        self._clear_pic = True
        self._refresh_avatar_preview()
        self._status_label.configure(text="Photo marked for removal ❌", text_color=ACCENT_YELLOW)

    def _save(self):
        if self._is_saving:
            return
        name = self._name_entry.get().strip()
        phone = self._phone_entry.get().strip()
        if not name or not phone:
            self._status_label.configure(
                text="Name and phone are required. / नाम और फ़ोन अनिवार्य हैं।",
                text_color=ACCENT_RED
            )
            return

        self._is_saving = True
        self._save_btn.configure(state="disabled", text="Saving…")
        self._status_label.configure(text="Saving to cloud database…", text_color=ACCENT_BLUE)

        threading.Thread(
            target=self._do_save,
            args=(name, phone, self._selected_pic_bytes, self._clear_pic),
            daemon=True
        ).start()

    def _do_save(self, name: str, phone: str, pic_bytes: bytes | None, clear_pic: bool):
        try:
            success = db_manager.update_user(
                user_id=self.user["id"],
                display_name=name,
                phone=phone,
                profile_pic_bytes=pic_bytes,
                clear_pic=clear_pic
            )
            if success:
                self.after(0, lambda: self._on_save_success(name, phone))
            else:
                self.after(0, lambda: self._on_save_fail("Phone number already taken by another user."))
        except Exception as e:
            self.after(0, lambda: self._on_save_fail(str(e)))

    def _on_save_success(self, name: str, phone: str):
        self.user["display_name"] = name
        self.user["phone"] = phone
        if self.on_saved:
            self.on_saved(self.user)
        self.destroy()

    def _on_save_fail(self, error_msg: str):
        self._is_saving = False
        self._save_btn.configure(state="normal", text="💾 Save Changes  ·  सहेजें")
        self._status_label.configure(text=f"Error: {error_msg}", text_color=ACCENT_RED)


# ═══════════════════════════════════════════════════════════════════════
# AdminPanel
# ═══════════════════════════════════════════════════════════════════════
class AdminPanel(ctk.CTk):
    def __init__(self, admin_user: dict):
        super().__init__()
        self.admin_user = admin_user
        self.title("Admin Panel  ·  एडमिन पैनल  —  Kanta's Crypto Alerts")
        self.geometry("900x660")
        self.minsize(800, 560)
        self.configure(fg_color=BG_MAIN)
        apply_window_icon(self)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self._selected_pic_bytes: bytes | None = None
        self._users: list[dict] = []

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._refresh_users()

    # ──────────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)
        hdr.pack(fill="x")

        logo = get_app_logo_image((36, 36))
        if logo:
            ctk.CTkLabel(hdr, image=logo, text="").pack(side="left", padx=(16, 8), pady=10)

        title_f = ctk.CTkFrame(hdr, fg_color="transparent")
        title_f.pack(side="left", pady=8)
        ctk.CTkLabel(title_f, text="Admin Panel  ·  एडमिन पैनल",
                     font=ctk.CTkFont("Segoe UI", 17, "bold"),
                     text_color=ACCENT_GREEN).pack(anchor="w")
        self._admin_name_lbl = ctk.CTkLabel(
            title_f, text=f"Logged in as: {self.admin_user.get('display_name', 'Admin')}",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=TEXT_SECONDARY)
        self._admin_name_lbl.pack(anchor="w")

        # Open Alerts button
        ctk.CTkButton(
            hdr, text="📈 Open Crypto Alerts\n    क्रिप्टो अलर्ट्स खोलें",
            width=175, height=48,
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color="#1a2a1a", hover_color="#1e3a1e",
            text_color=ACCENT_GREEN,
            border_width=1, border_color=ACCENT_GREEN,
            corner_radius=10,
            command=self._open_crypto_alerts
        ).pack(side="right", padx=12, pady=8)

        # Logout button
        ctk.CTkButton(
            hdr, text="🚪 Logout",
            width=90, height=48,
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color=BTN_DEFAULT, hover_color="#3d0f14",
            text_color=ACCENT_RED,
            corner_radius=10,
            command=self._logout
        ).pack(side="right", padx=6, pady=8)

        # ── Main content: left = users list, right = create + history ─
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=10)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        # ── Left: user list ──────────────────────────────────────────
        left = ctk.CTkFrame(content, fg_color=BG_PANEL, corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        lhdr = ctk.CTkFrame(left, fg_color="transparent")
        lhdr.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(lhdr, text="👥  Users  ·  उपयोगकर्ता",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left")
        ctk.CTkButton(lhdr, text="↻ Refresh", width=80, height=28,
                      font=ctk.CTkFont("Segoe UI", 10),
                      fg_color=BTN_DEFAULT, hover_color="#30363d",
                      text_color=ACCENT_BLUE,
                      command=self._refresh_users).pack(side="right")

        self._users_scroll = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self._users_scroll.pack(fill="both", expand=True, padx=6, pady=6)

        # ── Right: create user + history ─────────────────────────────
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        # Create user card
        create_card = ctk.CTkFrame(right, fg_color=BG_PANEL, corner_radius=12)
        create_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(create_card, text="➕  Create User  ·  नया उपयोगकर्ता",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=ACCENT_BLUE).pack(padx=14, pady=(12, 6), anchor="w")

        self._new_name = ctk.CTkEntry(create_card, width=240, height=36,
                                       placeholder_text="Full name  /  पूरा नाम",
                                       fg_color=BG_MAIN, border_color=BORDER_COLOR,
                                       text_color=TEXT_PRIMARY)
        self._new_name.pack(padx=14, pady=3, fill="x")

        self._new_phone = ctk.CTkEntry(create_card, width=240, height=36,
                                        placeholder_text="Phone number (password)  /  फ़ोन नंबर",
                                        fg_color=BG_MAIN, border_color=BORDER_COLOR,
                                        text_color=TEXT_PRIMARY)
        self._new_phone.pack(padx=14, pady=3, fill="x")

        pic_row = ctk.CTkFrame(create_card, fg_color="transparent")
        pic_row.pack(fill="x", padx=14, pady=4)

        self._pic_preview = ctk.CTkLabel(pic_row, text="", width=42, height=42)
        self._pic_preview.pack(side="left", padx=(0, 8))

        ctk.CTkButton(pic_row, text="📷 Upload Photo",
                      width=120, height=34,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color=BTN_DEFAULT, hover_color="#30363d",
                      text_color=ACCENT_BLUE,
                      command=self._pick_profile_pic).pack(side="left")

        self._create_status = ctk.CTkLabel(create_card, text="",
                                            font=ctk.CTkFont("Segoe UI", 10),
                                            text_color=TEXT_SECONDARY)
        self._create_status.pack(padx=14, pady=(2, 4))

        ctk.CTkButton(create_card, text="✅ Create User  ·  बनाएं",
                      height=38,
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      fg_color=ACCENT_GREEN, hover_color="#2d8f42",
                      text_color=BG_MAIN,
                      command=self._create_user).pack(fill="x", padx=14, pady=(0, 12))

        # Alert history card
        hist_card = ctk.CTkFrame(right, fg_color=BG_PANEL, corner_radius=12)
        hist_card.pack(fill="both", expand=True)

        hist_hdr = ctk.CTkFrame(hist_card, fg_color="transparent")
        hist_hdr.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(hist_hdr, text="🔔  Alert History  ·  अलर्ट इतिहास",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=ACCENT_YELLOW).pack(side="left")
        ctk.CTkButton(hist_hdr, text="↻", width=36, height=28,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color=BTN_DEFAULT, text_color=ACCENT_BLUE,
                      command=self._load_history).pack(side="right")

        self._history_scroll = ctk.CTkScrollableFrame(hist_card, fg_color="transparent", height=200)
        self._history_scroll.pack(fill="both", expand=True, padx=6, pady=6)

        # ── Status bar ───────────────────────────────────────────────
        self._status_bar = ctk.CTkLabel(self, text="",
                                         font=ctk.CTkFont("Segoe UI", 10),
                                         text_color=TEXT_SECONDARY)
        self._status_bar.pack(side="bottom", pady=4)

    # ──────────────────────────────────────────────────────────────────
    # Users list
    # ──────────────────────────────────────────────────────────────────

    def _refresh_users(self):
        self._status_bar.configure(text="Loading users…")
        threading.Thread(target=self._fetch_users, daemon=True).start()

    def _fetch_users(self):
        try:
            users = db_manager.get_all_users()
            self.after(0, lambda: self._render_users(users))
        except Exception as e:
            self.after(0, lambda: self._status_bar.configure(
                text=f"Error: {e}", text_color=ACCENT_RED))

    def _render_users(self, users: list[dict]):
        self._users = users
        for w in self._users_scroll.winfo_children():
            w.destroy()

        for i, user in enumerate(users):
            bg = BG_ROW_ALT if i % 2 else BG_ROW
            row = ctk.CTkFrame(self._users_scroll, fg_color=bg, corner_radius=8)
            row.pack(fill="x", pady=3, padx=2)

            # Profile pic
            pic_img = None
            if user.get("has_pic") or user.get("profile_pic"):
                try:
                    full = db_manager.get_user_by_id(user["id"])
                    if full and full.get("profile_pic"):
                        pic_img = load_profile_pic(full["profile_pic"], 38)
                except Exception:
                    pass

            if pic_img:
                ctk.CTkLabel(row, image=pic_img, text="", width=42, height=42).pack(
                    side="left", padx=(10, 6), pady=6)
            else:
                # Letter badge
                name = user.get("display_name", "?")
                badge = ctk.CTkLabel(row, text=name[0].upper(),
                                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                                     fg_color=ACCENT_BLUE, text_color=BG_MAIN,
                                     width=38, height=38, corner_radius=19)
                badge.pack(side="left", padx=(10, 6), pady=6)

            # Info
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=4)
            ctk.CTkLabel(info,
                         text=f"{user.get('display_name', '?')}  {'👑 Admin' if user.get('is_admin') else ''}",
                         font=ctk.CTkFont("Segoe UI", 12, "bold"),
                         text_color=ACCENT_GREEN if user.get("is_admin") else TEXT_PRIMARY,
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(info,
                         text=f"📱 {user.get('phone', '?')}",
                         font=ctk.CTkFont("Segoe UI", 10),
                         text_color=TEXT_SECONDARY,
                         anchor="w").pack(anchor="w")
            if user.get("last_login"):
                ctk.CTkLabel(info,
                              text=f"Last login: {str(user['last_login'])[:16]}",
                              font=ctk.CTkFont("Segoe UI", 9),
                              text_color=TEXT_SECONDARY,
                              anchor="w").pack(anchor="w")

            # Actions box on the right
            actions_f = ctk.CTkFrame(row, fg_color="transparent")
            actions_f.pack(side="right", padx=8, pady=4)

            # ✏️ Edit user button (available for all users, including Admin)
            ctk.CTkButton(
                actions_f, text="✏️ Edit",
                width=62, height=30,
                font=ctk.CTkFont("Segoe UI", 11),
                fg_color=BTN_DEFAULT, hover_color="#1f334a",
                text_color=ACCENT_BLUE,
                command=lambda u=user: self._open_edit_dialog(u)
            ).pack(side="left", padx=3)

            # Delete (not for admin)
            if not user.get("is_admin"):
                ctk.CTkButton(actions_f, text="🗑",
                              width=32, height=30,
                              font=ctk.CTkFont("Segoe UI", 12),
                              fg_color=BG_MAIN, hover_color="#3d0f14",
                              text_color=ACCENT_RED,
                              command=lambda uid=user["id"], n=user["display_name"]: self._confirm_delete(uid, n)
                              ).pack(side="left", padx=3)

        self._status_bar.configure(
            text=f"{len(users)} user(s) loaded  ·  {len(users)} उपयोगकर्ता",
            text_color=TEXT_SECONDARY
        )
        self._load_history()

    # ──────────────────────────────────────────────────────────────────
    # Create user
    # ──────────────────────────────────────────────────────────────────

    def _pick_profile_pic(self):
        path = filedialog.askopenfilename(
            title="Select Profile Picture / प्रोफ़ाइल चित्र चुनें",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            img = Image.open(path)
            # Limit size for DB storage
            img.thumbnail((400, 400), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            self._selected_pic_bytes = buf.getvalue()
            # Preview
            preview = make_circle_image(img, 42)
            self._pic_preview.configure(image=preview)
            self._create_status.configure(text="Photo selected ✓", text_color=ACCENT_GREEN)
        except Exception as e:
            self._create_status.configure(text=f"Image error: {e}", text_color=ACCENT_RED)

    def _create_user(self):
        name = self._new_name.get().strip()
        phone = self._new_phone.get().strip()
        if not name or not phone:
            self._create_status.configure(
                text="Name and phone are required.  /  नाम और फ़ोन आवश्यक है।",
                text_color=ACCENT_YELLOW
            )
            return

        threading.Thread(target=self._do_create, args=(name, phone), daemon=True).start()

    def _do_create(self, name: str, phone: str):
        try:
            existing = db_manager.get_user_by_phone(phone)
            if existing:
                self.after(0, lambda: self._create_status.configure(
                    text="Phone number already exists.  /  यह नंबर पहले से है।",
                    text_color=ACCENT_RED
                ))
                return
            db_manager.create_user(phone, name, is_admin=False,
                                   profile_pic_bytes=self._selected_pic_bytes)
            self.after(0, self._on_user_created)
        except Exception as e:
            self.after(0, lambda: self._create_status.configure(
                text=f"Error: {e}", text_color=ACCENT_RED))

    def _on_user_created(self):
        self._new_name.delete(0, tk.END)
        self._new_phone.delete(0, tk.END)
        self._selected_pic_bytes = None
        self._pic_preview.configure(image=None)
        self._create_status.configure(text="✅ User created!  /  उपयोगकर्ता बना दिया गया!", text_color=ACCENT_GREEN)
        self._refresh_users()

    # ──────────────────────────────────────────────────────────────────
    # Delete user
    # ──────────────────────────────────────────────────────────────────

    def _confirm_delete(self, user_id: int, name: str):
        ok = messagebox.askyesno(
            "Delete User  ·  उपयोगकर्ता हटाएं",
            f"Are you sure you want to delete '{name}'?\nSHIS will also delete all their data.\n\nक्या आप '{name}' को हटाना चाहते हैं? उनका सारा डेटा भी हट जाएगा।"
        )
        if ok:
            threading.Thread(target=lambda: self._do_delete(user_id), daemon=True).start()

    def _do_delete(self, user_id: int):
        try:
            db_manager.delete_user(user_id)
            self.after(0, self._refresh_users)
        except Exception as e:
            self.after(0, lambda: self._status_bar.configure(
                text=f"Delete error: {e}", text_color=ACCENT_RED))

    # ──────────────────────────────────────────────────────────────────
    # Edit user
    # ──────────────────────────────────────────────────────────────────

    def _open_edit_dialog(self, user: dict):
        def _on_user_saved(updated_user):
            if updated_user.get("id") == self.admin_user.get("id"):
                self.admin_user.update(updated_user)
                if hasattr(self, "_admin_name_lbl"):
                    self._admin_name_lbl.configure(
                        text=f"Logged in as: {self.admin_user.get('display_name', 'Admin')}"
                    )
            self._refresh_users()
            self._status_bar.configure(
                text=f"User '{updated_user.get('display_name')}' updated successfully! ✓",
                text_color=ACCENT_GREEN
            )

        EditUserDialog(self, user, on_saved=_on_user_saved)

    # ──────────────────────────────────────────────────────────────────
    # Alert history
    # ──────────────────────────────────────────────────────────────────

    def _load_history(self):
        threading.Thread(target=self._fetch_history, daemon=True).start()

    def _fetch_history(self):
        try:
            rows = db_manager.get_alert_history(user_id=None)  # all users
            self.after(0, lambda: self._render_history(rows))
        except Exception as e:
            print(f"[AdminPanel] History error: {e}")

    def _render_history(self, rows: list[dict]):
        for w in self._history_scroll.winfo_children():
            w.destroy()

        if not rows:
            ctk.CTkLabel(self._history_scroll,
                         text="No alert history yet.",
                         text_color=TEXT_SECONDARY).pack(pady=10)
            return

        for row in rows[:80]:
            arrow = "📈" if row.get("alert_type") == "above" else "📉"
            text = (
                f"{arrow} {row.get('symbol','')}  "
                f"{'above' if row.get('alert_type')=='above' else 'below'} "
                f"{row.get('threshold','')} USDT  "
                f"@ {row.get('trigger_price','')}  "
                f"—  {row.get('display_name','?')}  "
                f"[{str(row.get('triggered_at',''))[:16]}]"
            )
            ctk.CTkLabel(
                self._history_scroll, text=text,
                font=ctk.CTkFont("Segoe UI", 9),
                text_color=ACCENT_GREEN if row.get("alert_type") == "above" else ACCENT_RED,
                anchor="w"
            ).pack(fill="x", padx=4, pady=1)

    # ──────────────────────────────────────────────────────────────────
    # Open crypto alerts as admin
    # ──────────────────────────────────────────────────────────────────

    def _open_crypto_alerts(self):
        """Open the main App window while keeping admin panel open."""
        from gui import App
        app_win = ctk.CTkToplevel(self)
        app_win.withdraw()
        app_win.destroy()
        # Open in a new CTk root-like window (App is a CTk subclass)
        threading.Thread(target=self._launch_alerts_window, daemon=True).start()

    def _launch_alerts_window(self):
        from gui import App
        self.after(0, lambda: self._do_launch())

    def _do_launch(self):
        """Launch App as a Toplevel-like child (workaround for multiple CTk roots)."""
        from gui import App
        # Withdraw admin panel, open App, when App closes bring admin panel back
        self.withdraw()
        try:
            app = App(current_user=self.admin_user, on_close_callback=self.deiconify)
            app.mainloop()
        except Exception as e:
            print(f"[AdminPanel] App launch error: {e}")
            self.deiconify()

    # ──────────────────────────────────────────────────────────────────
    # Logout / close
    # ──────────────────────────────────────────────────────────────────

    def _logout(self):
        auth_manager.clear_local_session()
        self.destroy()
        from login_screen import LoginScreen
        ls = LoginScreen()
        ls.mainloop()

    def _on_close(self):
        auth_manager.clear_local_session()
        self.destroy()
