import customtkinter as ctk
import tkinter.ttk as ttk
from tkinter import messagebox, StringVar
import sqlite3
import hashlib
from datetime import datetime
import os

# تنظیمات ظاهری CustomTkinter
ctk.set_appearance_mode("dark")  # یا "light"
ctk.set_default_color_theme("blue")

VERSION = "beta 1.1 pre-Release 1"

class Database:
    def __init__(self, db_name="hsabet.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        # جدول کاربران
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        # جدول تراکنش‌ها با user_id برای چند کاربره
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def register_user(self, username, password):
        # هش کردن رمز
        hashed = hashlib.sha256(password.encode()).hexdigest()
        try:
            self.cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # کاربر تکراری

    def login_user(self, username, password):
        hashed = hashlib.sha256(password.encode()).hexdigest()
        self.cursor.execute("SELECT id FROM users WHERE username=? AND password_hash=?", (username, hashed))
        row = self.cursor.fetchone()
        if row:
            return row[0]  # برگرداندن user_id
        return None

    def add_transaction(self, user_id, t_type, category, amount, description):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        self.cursor.execute("""
            INSERT INTO transactions (user_id, type, category, amount, description, date, time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, t_type, category, amount, description, date_str, time_str))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_transactions(self, user_id, start_date=None, end_date=None, category=None):
        query = "SELECT id, type, category, amount, description, date, time FROM transactions WHERE user_id = ?"
        params = [user_id]
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY date DESC, time DESC"
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_transaction_by_id(self, t_id, user_id):
        self.cursor.execute("""
            SELECT id, type, category, amount, description, date, time
            FROM transactions WHERE id=? AND user_id=?
        """, (t_id, user_id))
        return self.cursor.fetchone()

    def update_transaction(self, t_id, user_id, t_type, category, amount, description):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        self.cursor.execute("""
            UPDATE transactions
            SET type=?, category=?, amount=?, description=?, date=?, time=?
            WHERE id=? AND user_id=?
        """, (t_type, category, amount, description, date_str, time_str, t_id, user_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_transaction(self, t_id, user_id):
        self.cursor.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (t_id, user_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_balance(self, user_id, start_date=None, end_date=None):
        query = """
            SELECT 
                SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as total_expense
            FROM transactions WHERE user_id=?
        """
        params = [user_id]
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        self.cursor.execute(query, params)
        row = self.cursor.fetchone()
        total_income = row[0] if row[0] else 0
        total_expense = row[1] if row[1] else 0
        balance = total_income - total_expense
        return total_income, total_expense, balance

    def get_categories(self, user_id):
        # برای نمایش لیست دسته‌بندی‌های موجود (اختیاری)
        self.cursor.execute("SELECT DISTINCT category FROM transactions WHERE user_id=? ORDER BY category", (user_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def close(self):
        self.conn.close()


# ---------- ویجت‌های گرافیکی ----------
class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"hsabet client - ورود ({VERSION})")
        self.geometry("400x500")
        self.resizable(False, False)
        self.db = Database()
        self.user_id = None

        # فریم اصلی
        self.frame = ctk.CTkFrame(self)
        self.frame.pack(pady=40, padx=40, fill="both", expand=True)

        ctk.CTkLabel(self.frame, text="💰 hsabet client", font=("Arial", 24, "bold")).pack(pady=20)
        ctk.CTkLabel(self.frame, text="ورود به حساب کاربری", font=("Arial", 14)).pack(pady=5)

        self.username_entry = ctk.CTkEntry(self.frame, placeholder_text="نام کاربری", width=250)
        self.username_entry.pack(pady=10)

        self.password_entry = ctk.CTkEntry(self.frame, placeholder_text="رمز عبور", show="*", width=250)
        self.password_entry.pack(pady=10)

        self.login_btn = ctk.CTkButton(self.frame, text="ورود", command=self.login)
        self.login_btn.pack(pady=10)

        self.register_btn = ctk.CTkButton(self.frame, text="ثبت‌نام", fg_color="green", command=self.open_register)
        self.register_btn.pack(pady=5)

        self.status_label = ctk.CTkLabel(self.frame, text="", text_color="red")
        self.status_label.pack(pady=5)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if not username or not password:
            self.status_label.configure(text="لطفاً همه فیلدها را پر کنید", text_color="red")
            return
        user_id = self.db.login_user(username, password)
        if user_id:
            self.user_id = user_id
            self.status_label.configure(text="", text_color="green")
            self.destroy()  # بستن پنجره لاگین
            self.open_main_app(user_id)
        else:
            self.status_label.configure(text="نام کاربری یا رمز اشتباه است", text_color="red")

    def open_register(self):
        RegisterWindow(self)

    def open_main_app(self, user_id):
        app = MainApp(user_id, self.db)
        app.mainloop()

    def on_close(self):
        self.db.close()
        self.destroy()


class RegisterWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("ثبت‌نام کاربر جدید")
        self.geometry("350x400")
        self.resizable(False, False)
        self.db = parent.db

        frame = ctk.CTkFrame(self)
        frame.pack(pady=30, padx=30, fill="both", expand=True)

        ctk.CTkLabel(frame, text="ثبت‌نام", font=("Arial", 20, "bold")).pack(pady=10)

        self.username_entry = ctk.CTkEntry(frame, placeholder_text="نام کاربری", width=200)
        self.username_entry.pack(pady=10)

        self.password_entry = ctk.CTkEntry(frame, placeholder_text="رمز عبور", show="*", width=200)
        self.password_entry.pack(pady=10)

        self.confirm_entry = ctk.CTkEntry(frame, placeholder_text="تکرار رمز عبور", show="*", width=200)
        self.confirm_entry.pack(pady=10)

        self.register_btn = ctk.CTkButton(frame, text="ثبت‌نام", command=self.register)
        self.register_btn.pack(pady=15)

        self.status_label = ctk.CTkLabel(frame, text="", text_color="red")
        self.status_label.pack()

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        if not username or not password or not confirm:
            self.status_label.configure(text="همه فیلدها اجباری هستند", text_color="red")
            return
        if password != confirm:
            self.status_label.configure(text="رمزها مطابقت ندارند", text_color="red")
            return
        if len(password) < 4:
            self.status_label.configure(text="رمز حداقل ۴ کاراکتر باشد", text_color="red")
            return
        success = self.db.register_user(username, password)
        if success:
            self.status_label.configure(text="ثبت‌نام موفق! حالا وارد شوید.", text_color="green")
            self.after(1500, self.destroy)  # بستن پنجره بعد از ۱.۵ ثانیه
        else:
            self.status_label.configure(text="این نام کاربری قبلاً ثبت شده است", text_color="red")


class MainApp(ctk.CTk):
    def __init__(self, user_id, db):
        super().__init__()
        self.user_id = user_id
        self.db = db
        self.title(f"hsabet client - مدیریت حسابداری ({VERSION})")
        self.geometry("1000x650")
        self.minsize(800, 500)

        # متغیرهای فیلتر
        self.filter_category = StringVar(value="همه")
        self.filter_start_date = StringVar()
        self.filter_end_date = StringVar()

        self.create_widgets()
        self.refresh_table()

        # بستن برنامه با بستن پنجره
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        # نوار منوی بالا
        menubar = ctk.CTkFrame(self, height=40, fg_color="transparent")
        menubar.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(menubar, text=f"خوش آمدید! (کاربر: {self.get_username()})", font=("Arial", 12)).pack(side="left", padx=10)
        logout_btn = ctk.CTkButton(menubar, text="خروج از سیستم", command=self.logout, width=100, fg_color="red")
        logout_btn.pack(side="right", padx=10)

        # فریم اصلی با دو ستون
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # قسمت چپ: خلاصه و افزودن تراکنش
        left_frame = ctk.CTkFrame(main_frame, width=300)
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        left_frame.pack_propagate(False)

        # خلاصه مالی
        summary_frame = ctk.CTkFrame(left_frame)
        summary_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(summary_frame, text="خلاصه مالی", font=("Arial", 16, "bold")).pack(pady=5)

        self.income_label = ctk.CTkLabel(summary_frame, text="درآمد: ۰ تومان", text_color="green")
        self.income_label.pack(anchor="w", padx=10)

        self.expense_label = ctk.CTkLabel(summary_frame, text="هزینه: ۰ تومان", text_color="red")
        self.expense_label.pack(anchor="w", padx=10)

        self.balance_label = ctk.CTkLabel(summary_frame, text="مانده: ۰ تومان", font=("Arial", 14, "bold"))
        self.balance_label.pack(anchor="w", padx=10, pady=5)

        # فرم افزودن تراکنش
        add_frame = ctk.CTkFrame(left_frame)
        add_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(add_frame, text="افزودن تراکنش جدید", font=("Arial", 14, "bold")).pack(pady=5)

        # نوع
        type_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        type_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(type_frame, text="نوع:").pack(side="left", padx=5)
        self.type_var = StringVar(value="income")
        income_radio = ctk.CTkRadioButton(type_frame, text="درآمد", variable=self.type_var, value="income")
        income_radio.pack(side="left", padx=5)
        expense_radio = ctk.CTkRadioButton(type_frame, text="هزینه", variable=self.type_var, value="expense")
        expense_radio.pack(side="left", padx=5)

        # دسته‌بندی
        cat_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        cat_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(cat_frame, text="دسته‌بندی:").pack(side="left", padx=5)
        self.category_entry = ctk.CTkEntry(cat_frame, placeholder_text="مثلاً خوراک، حقوق...", width=150)
        self.category_entry.pack(side="left", padx=5)

        # مبلغ
        amount_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        amount_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(amount_frame, text="مبلغ (تومان):").pack(side="left", padx=5)
        self.amount_entry = ctk.CTkEntry(amount_frame, width=150)
        self.amount_entry.pack(side="left", padx=5)

        # توضیحات
        desc_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        desc_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(desc_frame, text="توضیحات:").pack(side="left", padx=5)
        self.desc_entry = ctk.CTkEntry(desc_frame, width=180)
        self.desc_entry.pack(side="left", padx=5)

        add_btn = ctk.CTkButton(add_frame, text="ثبت تراکنش", command=self.add_transaction, fg_color="blue")
        add_btn.pack(pady=10)

        # قسمت راست: لیست تراکنش‌ها و فیلتر
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)

        # فیلترها
        filter_frame = ctk.CTkFrame(right_frame, height=50)
        filter_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(filter_frame, text="فیلتر:").pack(side="left", padx=5)

        # تاریخ شروع
        ctk.CTkLabel(filter_frame, text="از تاریخ:").pack(side="left", padx=5)
        self.start_date_entry = ctk.CTkEntry(filter_frame, placeholder_text="YYYY-MM-DD", width=100)
        self.start_date_entry.pack(side="left", padx=5)

        ctk.CTkLabel(filter_frame, text="تا تاریخ:").pack(side="left", padx=5)
        self.end_date_entry = ctk.CTkEntry(filter_frame, placeholder_text="YYYY-MM-DD", width=100)
        self.end_date_entry.pack(side="left", padx=5)

        ctk.CTkLabel(filter_frame, text="دسته:").pack(side="left", padx=5)
        self.category_filter_combo = ctk.CTkComboBox(filter_frame, values=["همه"], variable=self.filter_category, width=120)
        self.category_filter_combo.pack(side="left", padx=5)

        filter_btn = ctk.CTkButton(filter_frame, text="اعمال فیلتر", command=self.apply_filter, width=80)
        filter_btn.pack(side="left", padx=5)

        reset_btn = ctk.CTkButton(filter_frame, text="بازنشانی", command=self.reset_filter, width=80, fg_color="gray")
        reset_btn.pack(side="left", padx=5)

        # جدول نمایش تراکنش‌ها (با استفاده از ttk.Treeview)
        table_frame = ctk.CTkFrame(right_frame)
        table_frame.pack(fill="both", expand=True, pady=5)

        columns = ("id", "type", "category", "amount", "description", "date", "time")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        self.tree.heading("id", text="شناسه")
        self.tree.heading("type", text="نوع")
        self.tree.heading("category", text="دسته‌بندی")
        self.tree.heading("amount", text="مبلغ (تومان)")
        self.tree.heading("description", text="توضیحات")
        self.tree.heading("date", text="تاریخ")
        self.tree.heading("time", text="ساعت")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("type", width=70, anchor="center")
        self.tree.column("category", width=100, anchor="center")
        self.tree.column("amount", width=120, anchor="e")
        self.tree.column("description", width=200, anchor="w")
        self.tree.column("date", width=100, anchor="center")
        self.tree.column("time", width=80, anchor="center")

        # اسکرول بار
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # دکمه‌های عملیات روی جدول
        action_frame = ctk.CTkFrame(right_frame, height=40)
        action_frame.pack(fill="x", pady=5)

        edit_btn = ctk.CTkButton(action_frame, text="ویرایش انتخاب‌شده", command=self.edit_selected, width=120)
        edit_btn.pack(side="left", padx=5)

        delete_btn = ctk.CTkButton(action_frame, text="حذف انتخاب‌شده", command=self.delete_selected, width=120, fg_color="red")
        delete_btn.pack(side="left", padx=5)

        refresh_btn = ctk.CTkButton(action_frame, text="به‌روزرسانی", command=self.refresh_table, width=100)
        refresh_btn.pack(side="right", padx=5)

    def get_username(self):
        # دریافت نام کاربری از دیتابیس (برای نمایش)
        self.db.cursor.execute("SELECT username FROM users WHERE id=?", (self.user_id,))
        row = self.db.cursor.fetchone()
        return row[0] if row else "کاربر"

    def add_transaction(self):
        t_type = self.type_var.get()
        category = self.category_entry.get().strip()
        amount_str = self.amount_entry.get().strip()
        description = self.desc_entry.get().strip()

        if not category:
            messagebox.showerror("خطا", "لطفاً دسته‌بندی را وارد کنید")
            return
        if not amount_str:
            messagebox.showerror("خطا", "لطفاً مبلغ را وارد کنید")
            return
        try:
            amount = float(amount_str)
            if amount <= 0:
                messagebox.showerror("خطا", "مبلغ باید بزرگ‌تر از صفر باشد")
                return
        except ValueError:
            messagebox.showerror("خطا", "مبلغ را به صورت عدد وارد کنید")
            return

        # ثبت در دیتابیس
        self.db.add_transaction(self.user_id, t_type, category, amount, description)
        messagebox.showinfo("موفق", "تراکنش با موفقیت ثبت شد")
        # پاک کردن فیلدها
        self.category_entry.delete(0, "end")
        self.amount_entry.delete(0, "end")
        self.desc_entry.delete(0, "end")
        self.refresh_table()

    def refresh_table(self):
        # به‌روزرسانی لیست و خلاصه
        self.apply_filter()  # از فیلترهای فعلی استفاده می‌کند

    def apply_filter(self):
        start_date = self.start_date_entry.get().strip() or None
        end_date = self.end_date_entry.get().strip() or None
        category = self.filter_category.get()
        if category == "همه":
            category = None

        # دریافت تراکنش‌ها
        transactions = self.db.get_transactions(self.user_id, start_date, end_date, category)

        # پاک کردن جدول
        for row in self.tree.get_children():
            self.tree.delete(row)

        # پر کردن جدول
        for t in transactions:
            # t: (id, type, category, amount, description, date, time)
            type_display = "درآمد" if t[1] == "income" else "هزینه"
            amount_str = f"{t[3]:,}"
            self.tree.insert("", "end", values=(t[0], type_display, t[2], amount_str, t[4], t[5], t[6]))

        # به‌روزرسانی خلاصه
        total_income, total_expense, balance = self.db.get_balance(self.user_id, start_date, end_date)
        self.income_label.configure(text=f"درآمد: {total_income:,.0f} تومان")
        self.expense_label.configure(text=f"هزینه: {total_expense:,.0f} تومان")
        self.balance_label.configure(text=f"مانده: {balance:,.0f} تومان")

        # به‌روزرسانی لیست دسته‌بندی‌های فیلتر (با دسته‌های موجود)
        categories = self.db.get_categories(self.user_id)
        if "همه" not in categories:
            categories.insert(0, "همه")
        self.category_filter_combo.configure(values=categories)
        # اگر دسته‌ی انتخاب‌شده در لیست جدید نبود، آن را به "همه" تغییر دهیم
        if self.filter_category.get() not in categories:
            self.filter_category.set("همه")

    def reset_filter(self):
        self.start_date_entry.delete(0, "end")
        self.end_date_entry.delete(0, "end")
        self.filter_category.set("همه")
        self.apply_filter()

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("هشدار", "لطفاً یک تراکنش را انتخاب کنید")
            return
        # گرفتن id از ردیف انتخاب شده
        item = self.tree.item(selected[0])
        t_id = item['values'][0]
        # باز کردن پنجره ویرایش
        EditTransactionWindow(self, self.db, self.user_id, t_id, self.refresh_table)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("هشدار", "لطفاً یک تراکنش را انتخاب کنید")
            return
        item = self.tree.item(selected[0])
        t_id = item['values'][0]
        if messagebox.askyesno("تأیید حذف", f"آیا از حذف تراکنش شماره {t_id} مطمئن هستید؟"):
            self.db.delete_transaction(t_id, self.user_id)
            self.refresh_table()
            messagebox.showinfo("موفق", "تراکنش حذف شد")

    def logout(self):
        if messagebox.askyesno("خروج", "آیا می‌خواهید از سیستم خارج شوید؟"):
            self.destroy()
            # باز کردن مجدد پنجره لاگین
            login = LoginWindow()
            login.mainloop()

    def on_close(self):
        self.db.close()
        self.destroy()


class EditTransactionWindow(ctk.CTkToplevel):
    def __init__(self, parent, db, user_id, t_id, refresh_callback):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.user_id = user_id
        self.t_id = t_id
        self.refresh_callback = refresh_callback

        self.title("ویرایش تراکنش")
        self.geometry("400x400")
        self.resizable(False, False)

        # دریافت اطلاعات فعلی
        self.transaction = self.db.get_transaction_by_id(t_id, user_id)
        if not self.transaction:
            messagebox.showerror("خطا", "تراکنش پیدا نشد")
            self.destroy()
            return

        frame = ctk.CTkFrame(self)
        frame.pack(pady=20, padx=20, fill="both", expand=True)

        ctk.CTkLabel(frame, text="ویرایش تراکنش", font=("Arial", 18, "bold")).pack(pady=10)

        # نوع
        type_frame = ctk.CTkFrame(frame, fg_color="transparent")
        type_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(type_frame, text="نوع:").pack(side="left", padx=5)
        self.type_var = StringVar(value=self.transaction[1])  # income/expense
        income_radio = ctk.CTkRadioButton(type_frame, text="درآمد", variable=self.type_var, value="income")
        income_radio.pack(side="left", padx=5)
        expense_radio = ctk.CTkRadioButton(type_frame, text="هزینه", variable=self.type_var, value="expense")
        expense_radio.pack(side="left", padx=5)

        # دسته‌بندی
        cat_frame = ctk.CTkFrame(frame, fg_color="transparent")
        cat_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(cat_frame, text="دسته‌بندی:").pack(side="left", padx=5)
        self.category_entry = ctk.CTkEntry(cat_frame, width=200)
        self.category_entry.insert(0, self.transaction[2])
        self.category_entry.pack(side="left", padx=5)

        # مبلغ
        amount_frame = ctk.CTkFrame(frame, fg_color="transparent")
        amount_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(amount_frame, text="مبلغ (تومان):").pack(side="left", padx=5)
        self.amount_entry = ctk.CTkEntry(amount_frame, width=200)
        self.amount_entry.insert(0, str(self.transaction[3]))
        self.amount_entry.pack(side="left", padx=5)

        # توضیحات
        desc_frame = ctk.CTkFrame(frame, fg_color="transparent")
        desc_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(desc_frame, text="توضیحات:").pack(side="left", padx=5)
        self.desc_entry = ctk.CTkEntry(desc_frame, width=200)
        self.desc_entry.insert(0, self.transaction[4] if self.transaction[4] else "")
        self.desc_entry.pack(side="left", padx=5)

        # دکمه‌ها
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=20)

        save_btn = ctk.CTkButton(btn_frame, text="ذخیره تغییرات", command=self.save_changes, fg_color="green")
        save_btn.pack(side="left", padx=10)

        cancel_btn = ctk.CTkButton(btn_frame, text="انصراف", command=self.destroy, fg_color="gray")
        cancel_btn.pack(side="left", padx=10)

    def save_changes(self):
        t_type = self.type_var.get()
        category = self.category_entry.get().strip()
        amount_str = self.amount_entry.get().strip()
        description = self.desc_entry.get().strip()

        if not category:
            messagebox.showerror("خطا", "دسته‌بندی نمی‌تواند خالی باشد")
            return
        if not amount_str:
            messagebox.showerror("خطا", "لطفاً مبلغ را وارد کنید")
            return
        try:
            amount = float(amount_str)
            if amount <= 0:
                messagebox.showerror("خطا", "مبلغ باید بزرگ‌تر از صفر باشد")
                return
        except ValueError:
            messagebox.showerror("خطا", "مبلغ را به صورت عدد وارد کنید")
            return

        success = self.db.update_transaction(self.t_id, self.user_id, t_type, category, amount, description)
        if success:
            messagebox.showinfo("موفق", "تراکنش با موفقیت ویرایش شد")
            self.refresh_callback()
            self.destroy()
        else:
            messagebox.showerror("خطا", "ویرایش انجام نشد (مشکل در دیتابیس)")


# ---------- اجرای اصلی ----------
if __name__ == "__main__":
    login = LoginWindow()
    login.mainloop()