import tkinter as tk
from tkinter import messagebox
import math
from PIL import Image, ImageTk, ImageEnhance

try:
    import pygame.mixer
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

class MicrowaveOvenApp:
    def __init__(self, root):
        self.root = root
        root.title("Микроволновка")
        root.geometry("1000x700")
        root.resizable(False, False)

        self.food_files = {
            'Пицца': 'pizza.png',
            'Супик': 'soop.png',
            'Каша': 'kasha.png',
            'Чай': 'tea.png',
            'Картошка': 'potato.png',
        }

        self.splash_canvas = tk.Canvas(root, width=1000, height=700, highlightthickness=0)
        self.splash_canvas.pack()

        self.bg_image_orig = Image.open("1dab6da17e0739a51a04b07d6e615ab9.png").resize((1000, 700), Image.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(self.bg_image_orig)
        self.bg_item = self.splash_canvas.create_image(0, 0, anchor='nw', image=self.bg_photo)

        self.start_btn = tk.Button(root, text="СТАРТ", font=('Arial', 20, 'bold'),
                                   bg='lightgreen', command=self.start_fade)
        self.start_btn.place(x=450, y=620, width=100, height=50)

        self.fade_steps = 20
        self.current_step = 0

        self.preload_food_images()

    def preload_food_images(self):
        self.food_images = {}
        self.tk_food_images_main = {}
        for name, fname in self.food_files.items():
            img = Image.open(fname)
            self.food_images[name] = img
            self.tk_food_images_main[name] = ImageTk.PhotoImage(img.resize((140, 120), Image.LANCZOS))  # Внутри микроволновки

    def start_fade(self):
        self.start_btn.destroy()
        self.fade_out()

    def fade_out(self):
        if self.current_step <= self.fade_steps:
            alpha = 1.0 - (self.current_step / self.fade_steps)
            enhancer = ImageEnhance.Brightness(self.bg_image_orig)
            img = enhancer.enhance(alpha)
            self.bg_photo = ImageTk.PhotoImage(img)
            self.splash_canvas.itemconfig(self.bg_item, image=self.bg_photo)
            self.current_step += 1
            self.root.after(50, self.fade_out)
        else:
            self.splash_canvas.destroy()
            self.build_microwave_ui()

    def build_microwave_ui(self):
        self.door_open = False
        self.door_animating = False
        self.food_inside = None
        self.food_image_id = None
        self.pending_food = None
        self.food_is_hot = False
        self.is_running = False
        self.time_remaining = 0
        self.power_level = 0
        self.rotation_angle = 0

        if PYGAME_AVAILABLE:
            try:
                self.done_sound = pygame.mixer.Sound("beep.wav")
            except:
                self.done_sound = None
        else:
            self.done_sound = None

        self.create_ui()
        self.update_display()
        self.update_internal_light()

    def create_ui(self):
        self.canvas = tk.Canvas(self.root, width=1000, height=500, bg='#f5f0e6', highlightthickness=0)
        self.canvas.pack(fill='x')

        self.canvas.create_rectangle(0, 350, 1000, 400, fill='#8b5a2b', outline='')
        self.canvas.create_rectangle(300, 150, 700, 350, fill='#4a4a4a', outline='#222', width=3)
        self.canvas.create_rectangle(600, 160, 690, 340, fill='#2e2e2e', outline='#222', width=1)

        self.internal_display = self.canvas.create_text(645, 190, text="00:00",
                                                        font=('Arial', 16, 'bold'), fill='lime')

        self.start_rect = self.canvas.create_rectangle(610, 220, 680, 250,
                                                       fill='#4caf50', outline='#2e7d32', tags="start_btn")
        self.start_text = self.canvas.create_text(645, 235, text="Старт",
                                                  font=('Arial', 10, 'bold'), fill='white', tags="start_btn")
        self.canvas.tag_bind("start_btn", "<Button-1>", lambda e: self._on_canvas_start())

        self.menu_rect = self.canvas.create_rectangle(610, 260, 680, 290,
                                                      fill='#42a5f5', outline='#1e88e5', tags="menu_btn")
        self.menu_text = self.canvas.create_text(645, 275, text="Меню",
                                                 font=('Arial', 10, 'bold'), fill='white', tags="menu_btn")
        self.canvas.tag_bind("menu_btn", "<Button-1>", lambda e: self.open_food_menu())

        self.interior = self.canvas.create_rectangle(320, 180, 590, 320, fill='white', outline='')
        self.door_hinge_x = 320
        self.door_top = 180
        self.door_bottom = 320
        self.door_closed_right = 590
        self.door = self.canvas.create_rectangle(self.door_hinge_x, self.door_top,
                                                 self.door_closed_right, self.door_bottom,
                                                 fill='#5a5a5a', outline='#333', width=2)
        self.glass = self.canvas.create_rectangle(self.door_hinge_x + 8, self.door_top + 8,
                                                  self.door_closed_right - 8, self.door_bottom - 8,
                                                  fill='#e0f7fa', outline='#888', width=1)
        for item in (self.door, self.glass, self.interior):
            self.canvas.tag_bind(item, '<Button-1>', self.toggle_door)

        self.food_text = self.canvas.create_text(455, 250, text="", font=('Arial', 20, 'bold'), fill='saddlebrown')
        self.food_image_id = None
        self.heat_text = self.canvas.create_text(455, 285, text="", font=('Arial', 18), fill='red')

        self.btn_take = tk.Button(self.root, text="Достать", font=('Arial', 14),
                                  bg='lightgray', state='disabled',
                                  command=self.take_food, width=12)
        self.btn_take.pack(pady=10)

        ctrl_frame = tk.Frame(self.root, bg='#f0f0f0')
        ctrl_frame.pack(fill='x', pady=10)

        self.display_var = tk.StringVar()
        tk.Label(ctrl_frame, textvariable=self.display_var, font=('Arial', 20, 'bold'),
                 bg='black', fg='green', width=12).pack(pady=5)

        row1 = tk.Frame(ctrl_frame, bg='#f0f0f0')
        row1.pack()
        for d in (-10, -1, 1, 10):
            tk.Button(row1, text=f"{d:+}", font=('Arial', 12),
                      command=lambda x=d: self.adjust_time(x)).pack(side='left', padx=5)
        tk.Label(row1, text="Время (сек)", font=('Arial', 14), bg='#f0f0f0').pack(side='left', padx=15)

        row2 = tk.Frame(ctrl_frame, bg='#f0f0f0')
        row2.pack(pady=8)
        for d in (-100, -10, 10, 100):
            tk.Button(row2, text=f"{d:+}", font=('Arial', 12),
                      command=lambda x=d: self.adjust_power(x)).pack(side='left', padx=5)
        tk.Label(row2, text="Мощность (Вт)", font=('Arial', 14), bg='#f0f0f0').pack(side='left', padx=5)

        tk.Button(ctrl_frame, text="Отмена", font=('Arial', 14), bg='lightcoral',
                  command=self.cancel, width=12).pack(pady=10)

        self.status = tk.Label(self.root, text="Дверца закрыта", font=('Arial', 12),
                               bg='#f5f0e6', fg='gray')
        self.status.pack(pady=5)

    def _on_canvas_start(self):
        if self.is_running:
            self.stop_microwave()
        else:
            self.start_microwave()
        color = 'salmon' if self.is_running else '#4caf50'
        text = 'Стоп' if self.is_running else 'Старт'
        self.canvas.itemconfig(self.start_rect, fill=color)
        self.canvas.itemconfig(self.start_text, text=text)

    def adjust_time(self, d):
        self.time_remaining = max(0, min(999, self.time_remaining + d))
        self.update_display()

    def adjust_power(self, d):
        self.power_level = max(0, min(1000, self.power_level + d))
        self.update_display()

    def update_display(self):
        m, s = divmod(self.time_remaining, 60)
        self.display_var.set(f"{m:02d}:{s:02d}   {self.power_level}Вт")
        self.canvas.itemconfig(self.internal_display, text=f"{m:02d}:{s:02d}")

    def _validate(self):
        if self.door_open:
            return "Закройте дверцу!"
        if not self.food_inside:
            return "Добавьте еду!"
        if self.time_remaining <= 0:
            return "Установите время!"
        return None

    def start_microwave(self):
        err = self._validate()
        if err:
            return messagebox.showwarning("Ошибка", err)
        self.is_running = True
        self.status.config(text="Греется...")
        self.update_internal_light()
        self.animate_spin()
        self.run_timer()

    def animate_spin(self):
        if self.is_running and self.food_inside and self.food_image_id:
            self.rotation_angle = (self.rotation_angle + 8) % 360
            rad = math.radians(self.rotation_angle)
            dx = 50 * math.cos(rad)
            dy = 8 * math.sin(rad)
            self.canvas.coords(self.food_image_id, 455 + dx, 250 + dy)
            self.canvas.coords(self.heat_text, 455 + dx, 285 + dy)
            self.root.after(60, self.animate_spin)

    def run_timer(self):
        if self.is_running and self.time_remaining > 0:
            self.time_remaining -= 1
            self.update_display()
            self.root.after(1000, self.run_timer)
        elif self.is_running:
            self.is_running = False
            self.food_is_hot = True
            self.update_internal_light()
            self.update_heat_indicator()
            if self.done_sound:
                self.done_sound.play()
            self.status.config(text="Готово!")
            self.update_take()
            messagebox.showinfo("✅ Готово!", f"{self.food_inside} готова!\nОсторожно, горячо!")

    def stop_microwave(self):
        self.is_running = False
        self.status.config(text="Остановлена")
        self.update_internal_light()
        self.update_take()

    def cancel(self):
        if self.is_running:
            self.stop_microwave()
        self.time_remaining = 0
        self.power_level = 0
        self.update_display()
        self.status.config(text="Сброшено")

    def open_food_menu(self):
        win = tk.Toplevel(self.root)
        win.title("Выбор еды")
        win.geometry("250x300")
        win.transient(self.root)
        win.grab_set()
        win.focus_set()
        foods = [('🍕 Пицца', 'Пицца'), ('🍲 Супик', 'Супик'),
                 ('🥣 Каша', 'Каша'), ('☕ Чай', 'Чай'),
                 ('🥔 Картошка', 'Картошка')]
        for label, name in foods:
            tk.Button(win, text=label, font=('Arial', 14),
                      command=lambda n=name: self.select_food(n, win)).pack(fill='x', pady=5)

    def select_food(self, food, win):
        self.pending_food = food
        win.destroy()
        if self.door_open:
            self.place_food()
        else:
            messagebox.showinfo("Подсказка", f"Еда выбрана: {food}\nОткройте дверцу.")

    def place_food(self):
        if not self.pending_food:
            return
        self.food_inside = self.pending_food
        self.pending_food = None
        # удалить старое изображение еды, если оно есть
        if self.food_image_id:
            self.canvas.delete(self.food_image_id)
            self.food_image_id = None
        self.canvas.itemconfig(self.food_text, text="")
        img = self.tk_food_images_main.get(self.food_inside)
        if img:
            self.food_image_id = self.canvas.create_image(455, 250, image=img)
            self.canvas.image = img
        self.canvas.coords(self.heat_text, 455, 285)
        self.food_is_hot = False
        self.status.config(text=f"Еда внутри: {self.food_inside}")
        self.update_heat_indicator()
        self.update_take()

    def update_heat_indicator(self):
        txt = "🔥 ГОРЯЧО! 🔥" if self.food_is_hot else ""
        self.canvas.itemconfig(self.heat_text, text=txt)

    def toggle_door(self, _=None):
        if self.is_running or self.door_animating:
            return messagebox.showwarning("Предупреждение", "Остановите микроволновку!")
        self.door_open = not self.door_open
        self.door_animating = True
        self.animate_door(0)

    def animate_door(self, step):
        total_steps = 20
        if step > total_steps:
            self.door_animating = False
            self.status.config(text="Дверца открыта" if self.door_open else "Дверца закрыта")
            if self.door_open and self.pending_food:
                self.place_food()
            self.update_take()
            return
        angle_deg = (step / total_steps) * 90 if self.door_open else (1 - step / total_steps) * 90
        rad = math.radians(angle_deg)
        width = self.door_closed_right - self.door_hinge_x
        new_x = self.door_hinge_x + width * math.cos(rad)
        self.canvas.coords(self.door, self.door_hinge_x, self.door_top, new_x, self.door_bottom)
        self.canvas.coords(self.glass, self.door_hinge_x + 8, self.door_top + 8, new_x - 8, self.door_bottom - 8)
        self.root.after(20, lambda: self.animate_door(step + 1))

    def update_internal_light(self):
        fill_color = '#ffeb99' if self.is_running else 'white'
        self.canvas.itemconfig(self.interior, fill=fill_color)

    def update_take(self):
        ok = self.food_inside and self.door_open
        self.btn_take.config(state='normal' if ok else 'disabled')
        if ok:
            txt = "Достать (горячее)" if self.food_is_hot else "Достать"
            bg = 'orange' if self.food_is_hot else 'lightyellow'
            self.btn_take.config(text=txt, bg=bg)
        else:
            self.btn_take.config(text="Достать", bg='lightgray')

    def take_food(self):
        if self.food_is_hot:
            messagebox.showwarning("Осторожно!", f"{self.food_inside} горячее!")
        if self.food_image_id:
            self.canvas.delete(self.food_image_id)
            self.food_image_id = None
        self.canvas.itemconfig(self.food_text, text="")
        self.canvas.itemconfig(self.heat_text, text="")
        self.food_inside = None
        self.pending_food = None
        self.food_is_hot = False
        self.update_take()
        self.status.config(text="Еда удалена")


if __name__ == "__main__":
    root = tk.Tk()
    app = MicrowaveOvenApp(root)
    root.mainloop()
