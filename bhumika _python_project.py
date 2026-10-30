"""
PythonCab - Cab Ride Booking Analysis  (Tkinter Desktop Dashboard)
-------------------------------------------------------------------
Pages : Dashboard | Data Explorer | Charts (14) | Final Analysis
Needs : pip install pandas numpy matplotlib seaborn   (plotly optional)
Data  : cab_ride_booking_500_records.csv  (same folder as this file,
        or choose it from the file dialog)
"""

import os
import sys
import tempfile
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

try:
    import plotly.express as px
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False

CSV_NAME = "cab_ride_booking_500_records.csv"

# ----------------------------------------------------------------- THEME ---
BG       = "#0B1220"
SIDEBAR  = "#0F172A"
CARD     = "#162033"
CARD_HI  = "#1E2B45"
ACCENT   = "#FACC15"      # cab yellow
ACCENT_2 = "#38BDF8"
GOOD     = "#34D399"
BAD      = "#F87171"
WARN     = "#FB923C"
TEXT     = "#E5E7EB"
MUTED    = "#8B97AD"
PALETTE  = ["#FACC15", "#38BDF8", "#34D399", "#F472B6", "#A78BFA", "#FB923C",
            "#F87171", "#2DD4BF"]

FONT       = ("Segoe UI", 10)
FONT_B     = ("Segoe UI", 10, "bold")
FONT_H1    = ("Segoe UI", 20, "bold")
FONT_H2    = ("Segoe UI", 13, "bold")
FONT_KPI   = ("Segoe UI", 22, "bold")
FONT_SMALL = ("Segoe UI", 9)

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ------------------------------------------------------- DATA (Part 1) -----
def load_and_clean(path):
    """Same logic as part1() in the report, returned instead of printed."""
    raw = pd.read_csv(path)
    info = {
        "raw_shape": raw.shape,
        "columns": raw.columns.tolist(),
        "missing": raw.isnull().sum(),
        "duplicates": int(raw.duplicated().sum()),
    }

    df = raw.drop_duplicates().copy()
    for col in ["Ride_Distance_km", "Fare_INR", "Customer_Rating"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Fare_INR"] = df["Fare_INR"].fillna(df["Fare_INR"].median())
    df["Customer_Rating"] = df["Customer_Rating"].fillna(df["Customer_Rating"].median())
    df["Payment_Method"] = df["Payment_Method"].fillna(df["Payment_Method"].mode()[0])

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Time"] = pd.to_datetime(df["Time"], format="%H:%M", errors="coerce")

    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    df["Month_Name"] = df["Date"].dt.strftime("%b")
    df["Hour"] = df["Time"].dt.hour
    df["Revenue"] = np.where(df["Booking_Status"] == "Completed", df["Fare_INR"], 0)

    info["clean_shape"] = df.shape
    return df, info


def basic_stats(df):
    completed = df[df["Booking_Status"] == "Completed"]
    total = len(df)
    n_done = len(completed)
    corr = (np.corrcoef(completed["Ride_Distance_km"], completed["Fare_INR"])[0, 1]
            if n_done > 1 else float("nan"))
    rev_m = df.groupby("Month")["Revenue"].sum()
    rev_m_name = (df.groupby("Month")["Month_Name"].first()[rev_m.idxmax()]
                  if len(rev_m) else "-")
    veh_rev = df.groupby("Vehicle_Type")["Revenue"].sum()
    return {
        "total": total,
        "completed": n_done,
        "cancelled": int((df["Booking_Status"] == "Cancelled").sum()),
        "no_driver": int((df["Booking_Status"] == "No Driver Found").sum()),
        "revenue": df["Revenue"].sum(),
        "avg_fare": df["Fare_INR"].mean(),
        "avg_dist": df["Ride_Distance_km"].mean(),
        "avg_rating": df["Customer_Rating"].mean(),
        "top_vehicle": df["Vehicle_Type"].value_counts().idxmax(),
        "top_pickup": df["Pickup_Location"].value_counts().idxmax(),
        "top_drop": df["Drop_Location"].value_counts().idxmax(),
        "top_payment": df["Payment_Method"].value_counts().idxmax(),
        "busiest_hour": int(df["Hour"].value_counts().idxmax()),
        "top_rev_vehicle": veh_rev.idxmax(),
        "top_rev_month": rev_m_name,
        "corr": corr,
        "completion": n_done / total * 100 if total else 0,
    }


RECOMMENDATIONS = [
    "Increase vehicle availability during busy hours.",
    "Focus more vehicles on high-demand pickup locations.",
    "Improve driver availability to reduce failed bookings.",
    "Monitor cancelled bookings and identify their main causes.",
    "Promote digital payment methods if they are widely used.",
    "Maintain good service quality to keep customer ratings high.",
    "Focus on high-revenue vehicle categories.",
    "Use popular routes for targeted offers and promotions.",
]

CONCLUSION = ("The analysis helps understand booking patterns, vehicle demand, "
              "revenue, customer ratings, payment methods and popular locations. "
              "The results can help a cab company improve vehicle availability, "
              "reduce unsuccessful bookings and increase revenue.")


# ----------------------------------------------------- CHART HELPERS -------
def style_ax(ax, title, xlabel="", ylabel=""):
    ax.set_facecolor(CARD)
    ax.set_title(title, color=TEXT, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.tick_params(colors=MUTED)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#2A3752")
    ax.grid(axis="y", color="#2A3752", linestyle="--", linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)


def bar_chart(fig, series, title, xlabel="", ylabel="", horizontal=False,
              rotate=0, money=False):
    ax = fig.add_subplot(111)
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(series))]
    if horizontal:
        bars = ax.barh(series.index.astype(str), series.values, color=colors)
        ax.invert_yaxis()
        ax.grid(axis="x", color="#2A3752", linestyle="--", linewidth=0.6, alpha=0.7)
    else:
        bars = ax.bar(series.index.astype(str), series.values, color=colors,
                      width=0.65)
    style_ax(ax, title, xlabel, ylabel)
    if horizontal:
        ax.grid(axis="y", visible=False)
    fmt = (lambda v: f"₹{v:,.0f}") if money else (lambda v: f"{v:,.0f}")
    ax.bar_label(bars, labels=[fmt(v) for v in series.values], color=TEXT,
                 fontsize=9, padding=3)
    if rotate:
        for lbl in ax.get_xticklabels():
            lbl.set_rotation(rotate)
            lbl.set_ha("right")
    return ax


def month_series(df, col=None):
    """Chronologically-ordered monthly series (the report's groupby sorts A-Z)."""
    if col is None:
        s = df.groupby("Month_Name").size()
    else:
        s = df.groupby("Month_Name")[col].sum()
    order = [m for m in MONTH_ORDER if m in s.index]
    return s.reindex(order)


# ------------------------------------------------- 14 CHART DEFINITIONS -----
def c_status(fig, df):
    bar_chart(fig, df["Booking_Status"].value_counts(), "Booking Status",
              "Status", "Bookings")

def c_vehicle(fig, df):
    bar_chart(fig, df["Vehicle_Type"].value_counts(), "Bookings by Vehicle Type",
              "Vehicle", "Bookings")

def c_monthly_bookings(fig, df):
    bar_chart(fig, month_series(df), "Monthly Bookings", "Month", "Bookings")

def c_monthly_revenue(fig, df):
    bar_chart(fig, month_series(df, "Revenue"), "Monthly Revenue", "Month",
              "Revenue (₹)", money=True)

def c_pickup(fig, df):
    bar_chart(fig, df["Pickup_Location"].value_counts().head(10),
              "Top Pickup Locations", "Bookings", "", horizontal=True)

def c_drop(fig, df):
    bar_chart(fig, df["Drop_Location"].value_counts().head(10),
              "Top Drop Locations", "", "Bookings", rotate=40)

def c_veh_revenue(fig, df):
    bar_chart(fig, df.groupby("Vehicle_Type")["Revenue"].sum()
              .sort_values(ascending=False),
              "Revenue by Vehicle Type", "Vehicle", "Revenue (₹)", money=True)

def c_fare_hist(fig, df):
    ax = fig.add_subplot(111)
    sns.histplot(df["Fare_INR"], bins=20, kde=True, color=ACCENT, ax=ax,
                 edgecolor=CARD)
    style_ax(ax, "Fare Distribution", "Fare (₹)", "Count")

def c_rating_hist(fig, df):
    ax = fig.add_subplot(111)
    sns.histplot(df["Customer_Rating"], bins=10, kde=True, color=ACCENT_2,
                 ax=ax, edgecolor=CARD)
    style_ax(ax, "Customer Rating Distribution", "Rating", "Count")

def c_payment(fig, df):
    bar_chart(fig, df["Payment_Method"].value_counts(), "Payment Methods",
              "Method", "Bookings")

def c_hourly(fig, df):
    ax = fig.add_subplot(111)
    h = df["Hour"].value_counts().sort_index()
    ax.plot(h.index, h.values, marker="o", color=ACCENT, linewidth=2.4,
            markersize=7, markerfacecolor=BG, markeredgewidth=2)
    ax.fill_between(h.index, h.values, color=ACCENT, alpha=0.12)
    peak = h.idxmax()
    ax.annotate(f"Peak: {peak}:00", (peak, h.max()), color=TEXT,
                xytext=(0, 14), textcoords="offset points", ha="center",
                fontweight="bold")
    style_ax(ax, "Bookings by Hour", "Hour of day", "Bookings")
    ax.set_ylim(0, h.max() * 1.18)
    ax.grid(axis="x", color="#2A3752", linestyle="--", linewidth=0.6, alpha=0.5)

def c_scatter(fig, df):
    ax = fig.add_subplot(111)
    done = df[df["Booking_Status"] == "Completed"]
    sns.scatterplot(data=done, x="Ride_Distance_km", y="Fare_INR", color=ACCENT_2,
                    alpha=0.75, edgecolor="none", s=45, ax=ax)
    if len(done) > 1:
        m, b = np.polyfit(done["Ride_Distance_km"], done["Fare_INR"], 1)
        xs = np.linspace(done["Ride_Distance_km"].min(),
                         done["Ride_Distance_km"].max(), 50)
        ax.plot(xs, m * xs + b, color=ACCENT, linewidth=2, label="Trend")
        ax.legend(facecolor=CARD, edgecolor="#2A3752", labelcolor=TEXT)
    style_ax(ax, "Distance vs Fare (Completed rides)", "Distance (km)", "Fare (₹)")

def c_box(fig, df):
    ax = fig.add_subplot(111)
    done = df[df["Booking_Status"] == "Completed"]
    groups = sorted(done["Vehicle_Type"].unique())
    data = [done.loc[done["Vehicle_Type"] == g, "Customer_Rating"] for g in groups]
    try:                                   # Matplotlib 3.9+
        bp = ax.boxplot(data, patch_artist=True, tick_labels=groups)
    except TypeError:                      # older Matplotlib
        bp = ax.boxplot(data, patch_artist=True, labels=groups)
    for patch, col in zip(bp["boxes"], PALETTE):
        patch.set_facecolor(col)
        patch.set_alpha(0.85)
        patch.set_edgecolor(BG)
    for key in ("whiskers", "caps"):
        for item in bp[key]:
            item.set_color(MUTED)
    for item in bp["medians"]:
        item.set_color(BG)
        item.set_linewidth(2)
    for item in bp["fliers"]:
        item.set(marker="o", markerfacecolor=MUTED, markeredgecolor="none",
                 alpha=0.6)
    style_ax(ax, "Vehicle Type vs Customer Rating", "Vehicle", "Rating")

def top_routes(df):
    return (df.groupby(["Pickup_Location", "Drop_Location"]).size()
            .reset_index(name="Bookings")
            .sort_values("Bookings", ascending=False).head(10))

def c_routes(fig, df):
    r = top_routes(df)
    s = pd.Series(r["Bookings"].values,
                  index=[f"{a} → {b}" for a, b in
                         zip(r["Pickup_Location"], r["Drop_Location"])])
    bar_chart(fig, s, "Top 10 Routes", "Bookings", "", horizontal=True)


CHARTS = [
    ("1  Booking Status",          c_status),
    ("2  Bookings by Vehicle",     c_vehicle),
    ("3  Monthly Bookings",        c_monthly_bookings),
    ("4  Monthly Revenue",         c_monthly_revenue),
    ("5  Top Pickup Locations",    c_pickup),
    ("6  Top Drop Locations",      c_drop),
    ("7  Revenue by Vehicle",      c_veh_revenue),
    ("8  Fare Distribution",       c_fare_hist),
    ("9  Rating Distribution",     c_rating_hist),
    ("10  Payment Methods",        c_payment),
    ("11  Bookings by Hour",       c_hourly),
    ("12  Distance vs Fare",       c_scatter),
    ("13  Vehicle vs Rating",      c_box),
    ("14  Top 10 Routes",          c_routes),
]


# ------------------------------------------------------------ WIDGETS ------
class HoverButton(tk.Label):
    """Flat label that behaves like a button, with hover + active state."""

    def __init__(self, parent, text, command, **kw):
        self.normal = kw.pop("bg", SIDEBAR)
        self.hover = kw.pop("hover", CARD_HI)
        self.active_bg = kw.pop("active_bg", CARD)
        super().__init__(parent, text=text, bg=self.normal, cursor="hand2",
                         fg=kw.pop("fg", TEXT), font=kw.pop("font", FONT_B),
                         anchor=kw.pop("anchor", "w"), **kw)
        self.command = command
        self.active = False
        self.bind("<Enter>", lambda e: self._paint(True))
        self.bind("<Leave>", lambda e: self._paint(False))
        self.bind("<Button-1>", lambda e: self.command())

    def _paint(self, over):
        if self.active:
            self.config(bg=self.active_bg)
        else:
            self.config(bg=self.hover if over else self.normal)

    def set_active(self, flag):
        self.active = flag
        self.config(bg=self.active_bg if flag else self.normal,
                    fg=ACCENT if flag else TEXT)


class Card(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=CARD, highlightthickness=1,
                         highlightbackground="#22304B", **kw)


class KPI(Card):
    def __init__(self, parent, icon, title, value, color=ACCENT):
        super().__init__(parent, padx=16, pady=14)
        tk.Frame(self, bg=color, width=4).pack(side="left", fill="y", padx=(0, 12))
        box = tk.Frame(self, bg=CARD)
        box.pack(side="left", fill="both", expand=True)
        tk.Label(box, text=f"{icon}  {title}", bg=CARD, fg=MUTED,
                 font=FONT_SMALL).pack(anchor="w")
        self.val = tk.Label(box, text=value, bg=CARD, fg=TEXT, font=FONT_KPI)
        self.val.pack(anchor="w", pady=(4, 0))


# --------------------------------------------------------------- APP -------
class CabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PythonCab  •  Ride Booking Analysis")
        self.geometry("1280x780")
        self.minsize(1080, 680)
        self.configure(bg=BG)

        self.df = None
        self.info = None
        self.stats = None
        self.pages = {}
        self.nav = {}
        self.current = None
        self.chart_idx = 0
        self.canvas = None
        self.toolbar = None

        self._style()
        self._layout()

        if not self._auto_load():
            self.destroy()
            sys.exit(0)
        self._build_pages()
        self.show("Dashboard")

    # ------------------------------------------------------------ style ---
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Treeview", background=CARD, fieldbackground=CARD,
                    foreground=TEXT, rowheight=28, borderwidth=0, font=FONT)
        s.configure("Treeview.Heading", background=CARD_HI, foreground=ACCENT,
                    font=FONT_B, relief="flat", padding=6)
        s.map("Treeview", background=[("selected", "#2B3E63")],
              foreground=[("selected", "#FFFFFF")])
        s.map("Treeview.Heading", background=[("active", "#2B3E63")])
        s.configure("TCombobox", fieldbackground=CARD_HI, background=CARD_HI,
                    foreground=TEXT, arrowcolor=ACCENT, borderwidth=0)
        s.configure("Vertical.TScrollbar", background=CARD_HI, troughcolor=CARD,
                    arrowcolor=MUTED, borderwidth=0)
        s.configure("Horizontal.TScrollbar", background=CARD_HI, troughcolor=CARD,
                    arrowcolor=MUTED, borderwidth=0)
        s.configure("Yellow.Horizontal.TProgressbar", troughcolor=CARD_HI,
                    background=ACCENT, borderwidth=0, thickness=14)
        self.option_add("*TCombobox*Listbox.background", CARD_HI)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)

    # ----------------------------------------------------------- layout ---
    def _layout(self):
        side = tk.Frame(self, bg=SIDEBAR, width=230)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        logo = tk.Frame(side, bg=SIDEBAR)
        logo.pack(fill="x", padx=20, pady=(26, 6))
        tk.Label(logo, text="🚖", bg=SIDEBAR, font=("Segoe UI Emoji", 26)).pack(side="left")
        t = tk.Frame(logo, bg=SIDEBAR)
        t.pack(side="left", padx=10)
        tk.Label(t, text="PythonCab", bg=SIDEBAR, fg=ACCENT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(t, text="Ride Analytics", bg=SIDEBAR, fg=MUTED,
                 font=FONT_SMALL).pack(anchor="w")

        tk.Frame(side, bg="#1C2740", height=1).pack(fill="x", padx=20, pady=18)

        for name, icon in [("Dashboard", "📊"), ("Data Explorer", "🗂"),
                           ("Charts", "📈"), ("Final Analysis", "🧠")]:
            b = HoverButton(side, f"   {icon}   {name}",
                            lambda n=name: self.show(n), padx=12, pady=11)
            b.pack(fill="x", padx=12, pady=2)
            self.nav[name] = b

        tk.Frame(side, bg=SIDEBAR).pack(expand=True, fill="both")

        HoverButton(side, "   📂   Open CSV…", self.choose_file, padx=12, pady=11,
                    bg=CARD, hover=CARD_HI, fg=ACCENT
                    ).pack(fill="x", padx=12, pady=(0, 6))
        self.file_lbl = tk.Label(side, text="", bg=SIDEBAR, fg=MUTED,
                                 font=FONT_SMALL, wraplength=190, justify="left")
        self.file_lbl.pack(anchor="w", padx=20, pady=(0, 18))

        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        head = tk.Frame(right, bg=BG)
        head.pack(fill="x", padx=30, pady=(22, 6))
        self.title_lbl = tk.Label(head, text="", bg=BG, fg=TEXT, font=FONT_H1)
        self.title_lbl.pack(side="left")
        self.sub_lbl = tk.Label(head, text="", bg=BG, fg=MUTED, font=FONT)
        self.sub_lbl.pack(side="left", padx=14, pady=(8, 0))

        self.body = tk.Frame(right, bg=BG)
        self.body.pack(fill="both", expand=True, padx=30, pady=(6, 24))

    # ------------------------------------------------------------ data ----
    def _auto_load(self):
        here = os.path.dirname(os.path.abspath(__file__))
        for p in (os.path.join(here, CSV_NAME), os.path.join(os.getcwd(), CSV_NAME)):
            if os.path.exists(p):
                return self._load(p)
        messagebox.showinfo("Select dataset",
                            f"'{CSV_NAME}' was not found next to this script.\n"
                            "Please select the CSV file.")
        return self.choose_file(initial=True)

    def _load(self, path):
        try:
            self.df, self.info = load_and_clean(path)
            self.stats = basic_stats(self.df)
        except Exception as e:
            messagebox.showerror("Could not load file",
                                 f"{os.path.basename(path)}\n\n{e}")
            return False
        self.file_lbl.config(text=f"📄 {os.path.basename(path)}\n"
                                  f"{len(self.df)} records")
        return True

    def choose_file(self, initial=False):
        path = filedialog.askopenfilename(
            title="Select cab booking CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return False
        if not self._load(path):
            return False
        if not initial:
            self._build_pages()
            self.show(self.current or "Dashboard")
        return True

    # ------------------------------------------------------------ pages ---
    def _build_pages(self):
        for f in self.pages.values():
            f.destroy()
        self.pages = {}
        self.canvas = None
        self.toolbar = None
        self.pages["Dashboard"] = self._page_dashboard()
        self.pages["Data Explorer"] = self._page_data()
        self.pages["Charts"] = self._page_charts()
        self.pages["Final Analysis"] = self._page_analysis()

    SUBS = {
        "Dashboard": "Key numbers at a glance",
        "Data Explorer": "Browse and filter the cleaned dataset",
        "Charts": "14 visualisations from the report",
        "Final Analysis": "Insights, recommendations and conclusion",
    }

    def show(self, name):
        self.current = name
        for n, f in self.pages.items():
            f.pack_forget()
        self.pages[name].pack(in_=self.body, fill="both", expand=True)
        for n, b in self.nav.items():
            b.set_active(n == name)
        self.title_lbl.config(text=name)
        self.sub_lbl.config(text=self.SUBS[name])
        if name == "Charts":
            self.draw_chart(self.chart_idx)

    # -------------------------------------------------------- dashboard ---
    def _page_dashboard(self):
        s = self.stats
        page = tk.Frame(self.body, bg=BG)

        grid = tk.Frame(page, bg=BG)
        grid.pack(fill="x")
        kpis = [
            ("🧾", "Total Bookings", f"{s['total']:,}", ACCENT),
            ("✅", "Completed", f"{s['completed']:,}", GOOD),
            ("❌", "Cancelled", f"{s['cancelled']:,}", BAD),
            ("🚫", "No Driver Found", f"{s['no_driver']:,}", WARN),
            ("💰", "Total Revenue", f"₹{s['revenue']:,.0f}", ACCENT),
            ("🎟", "Average Fare", f"₹{s['avg_fare']:,.2f}", ACCENT_2),
            ("📏", "Average Distance", f"{s['avg_dist']:.2f} km", ACCENT_2),
            ("⭐", "Average Rating", f"{s['avg_rating']:.2f} / 5", "#A78BFA"),
        ]
        for i, (ic, t, v, c) in enumerate(kpis):
            KPI(grid, ic, t, v, c).grid(row=i // 4, column=i % 4, padx=6, pady=6,
                                        sticky="nsew")
        for c in range(4):
            grid.columnconfigure(c, weight=1, uniform="k")

        lower = tk.Frame(page, bg=BG)
        lower.pack(fill="both", expand=True, pady=(10, 0))
        lower.columnconfigure(0, weight=3, uniform="l")
        lower.columnconfigure(1, weight=2, uniform="l")
        lower.rowconfigure(0, weight=1)

        # left: quick insights + completion bar
        left = Card(lower, padx=22, pady=18)
        left.grid(row=0, column=0, sticky="nsew", padx=(6, 6), pady=6)
        tk.Label(left, text="Quick Insights", bg=CARD, fg=TEXT,
                 font=FONT_H2).pack(anchor="w")

        rate = s["completion"]
        tk.Label(left, text=f"Completion rate  {rate:.2f}%", bg=CARD, fg=MUTED,
                 font=FONT).pack(anchor="w", pady=(14, 4))
        ttk.Progressbar(left, style="Yellow.Horizontal.TProgressbar",
                        value=rate, maximum=100).pack(fill="x")
        tk.Label(left, text=f"{100 - rate:.2f}% of bookings did not result in a ride",
                 bg=CARD, fg=MUTED, font=FONT_SMALL).pack(anchor="w", pady=(4, 14))

        facts = [
            ("🚗  Most used vehicle", s["top_vehicle"]),
            ("📍  Top pickup location", s["top_pickup"]),
            ("🏁  Top drop location", s["top_drop"]),
            ("💳  Popular payment", s["top_payment"]),
            ("🕙  Busiest hour", f"{s['busiest_hour']:02d}:00"),
            ("🏆  Highest-revenue vehicle", s["top_rev_vehicle"]),
        ]
        for i, (k, v) in enumerate(facts):
            row = tk.Frame(left, bg=CARD if i % 2 == 0 else "#121C2E")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=k, bg=row["bg"], fg=MUTED, font=FONT,
                     padx=10, pady=7).pack(side="left")
            tk.Label(row, text=v, bg=row["bg"], fg=ACCENT, font=FONT_B,
                     padx=10).pack(side="right")

        # right: donut chart
        right = Card(lower)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 6), pady=6)
        fig = Figure(figsize=(4, 3.6), dpi=100, facecolor=CARD)
        ax = fig.add_subplot(111)
        counts = self.df["Booking_Status"].value_counts()
        wedges, _, autot = ax.pie(
            counts.values, colors=[GOOD, BAD, WARN, ACCENT_2][:len(counts)],
            autopct="%1.1f%%", pctdistance=0.8, startangle=90,
            wedgeprops=dict(width=0.38, edgecolor=CARD, linewidth=2))
        for t in autot:
            t.set_color(BG)
            t.set_fontweight("bold")
            t.set_fontsize(9)
        ax.legend(wedges, counts.index, loc="lower center", ncol=3, frameon=False,
                  labelcolor=TEXT, fontsize=8, bbox_to_anchor=(0.5, -0.08))
        ax.set_title("Booking Outcome", color=TEXT, fontsize=12, fontweight="bold")
        c = FigureCanvasTkAgg(fig, master=right)
        c.draw()
        c.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)
        return page

    # ------------------------------------------------------ data explorer -
    def _page_data(self):
        page = tk.Frame(self.body, bg=BG)

        bar = tk.Frame(page, bg=BG)
        bar.pack(fill="x", pady=(0, 10))
        tk.Label(bar, text="🔍", bg=BG, fg=ACCENT, font=("Segoe UI Emoji", 12)
                 ).pack(side="left")
        self.search_var = tk.StringVar()
        ent = tk.Entry(bar, textvariable=self.search_var, bg=CARD_HI, fg=TEXT,
                       insertbackground=ACCENT, relief="flat", font=FONT, width=34)
        ent.pack(side="left", padx=8, ipady=6)

        tk.Label(bar, text="Status:", bg=BG, fg=MUTED, font=FONT
                 ).pack(side="left", padx=(18, 6))
        self.status_var = tk.StringVar(value="All")
        statuses = ["All"] + sorted(self.df["Booking_Status"].unique())
        cb = ttk.Combobox(bar, textvariable=self.status_var, values=statuses,
                          state="readonly", width=16)
        cb.pack(side="left")
        self.count_lbl = tk.Label(bar, text="", bg=BG, fg=MUTED, font=FONT)
        self.count_lbl.pack(side="right")

        wrap = Card(page)
        wrap.pack(fill="both", expand=True)
        cols = ["Booking_ID", "Date", "Time", "Vehicle_Type", "Pickup_Location",
                "Drop_Location", "Booking_Status", "Ride_Distance_km",
                "Fare_INR", "Customer_Rating", "Payment_Method", "Revenue"]
        cols = [c for c in cols if c in self.df.columns]
        self.tree_cols = cols
        tree = ttk.Treeview(wrap, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c.replace("_", " "))
            tree.column(c, width=105, anchor="center")
        tree.tag_configure("odd", background="#121C2E")
        tree.tag_configure("even", background=CARD)
        vs = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        hs = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.pack(side="right", fill="y")
        hs.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)
        self.tree = tree

        self.search_var.trace_add("write", lambda *_: self._fill_table())
        cb.bind("<<ComboboxSelected>>", lambda e: self._fill_table())
        self._fill_table()
        return page

    def _fill_table(self):
        d = self.df
        if self.status_var.get() != "All":
            d = d[d["Booking_Status"] == self.status_var.get()]
        q = self.search_var.get().strip().lower()
        if q:
            mask = d[self.tree_cols].astype(str).apply(
                lambda col: col.str.lower().str.contains(q, regex=False)).any(axis=1)
            d = d[mask]
        self.tree.delete(*self.tree.get_children())
        for i, (_, r) in enumerate(d.iterrows()):
            vals = []
            for c in self.tree_cols:
                v = r[c]
                if c == "Date":
                    v = v.strftime("%Y-%m-%d") if pd.notna(v) else ""
                elif c == "Time":
                    v = v.strftime("%H:%M") if pd.notna(v) else ""
                elif isinstance(v, float):
                    v = f"{v:,.2f}"
                vals.append(v)
            self.tree.insert("", "end", values=vals,
                             tags=("odd" if i % 2 else "even",))
        self.count_lbl.config(text=f"{len(d):,} of {len(self.df):,} rows")

    # ------------------------------------------------------------ charts --
    def _page_charts(self):
        page = tk.Frame(self.body, bg=BG)

        menu = Card(page, width=220)
        menu.pack(side="left", fill="y", padx=(0, 12))
        menu.pack_propagate(False)
        tk.Label(menu, text="Select chart", bg=CARD, fg=MUTED, font=FONT_SMALL
                 ).pack(anchor="w", padx=14, pady=(12, 4))
        self.chart_btns = []
        for i, (name, _) in enumerate(CHARTS):
            b = HoverButton(menu, name, lambda k=i: self.draw_chart(k),
                            bg=CARD, hover=CARD_HI, active_bg="#2B3E63",
                            padx=14, pady=6, font=FONT)
            b.pack(fill="x", padx=6, pady=1)
            self.chart_btns.append(b)

        self.chart_area = Card(page)
        self.chart_area.pack(side="left", fill="both", expand=True)

        nav = tk.Frame(self.chart_area, bg=CARD)
        nav.pack(side="bottom", fill="x", padx=10, pady=8)
        self.tb_holder = tk.Frame(nav, bg=CARD)
        self.tb_holder.pack(side="left")
        HoverButton(nav, "Next ▶", lambda: self.draw_chart(
            (self.chart_idx + 1) % len(CHARTS)), bg=CARD_HI, hover="#2B3E63",
            fg=ACCENT, padx=14, pady=6, anchor="center").pack(side="right", padx=4)
        HoverButton(nav, "◀ Prev", lambda: self.draw_chart(
            (self.chart_idx - 1) % len(CHARTS)), bg=CARD_HI, hover="#2B3E63",
            fg=ACCENT, padx=14, pady=6, anchor="center").pack(side="right", padx=4)
        self.plotly_btn = HoverButton(
            nav, "🌐 Interactive (Plotly)", self.open_plotly, bg=CARD_HI,
            hover="#2B3E63", fg=ACCENT_2, padx=14, pady=6, anchor="center")
        self.canvas_holder = tk.Frame(self.chart_area, bg=CARD)
        self.canvas_holder.pack(fill="both", expand=True, padx=8, pady=8)
        return page

    def draw_chart(self, idx):
        self.chart_idx = idx
        for i, b in enumerate(self.chart_btns):
            b.set_active(i == idx)
        for w in self.canvas_holder.winfo_children():
            w.destroy()
        for w in self.tb_holder.winfo_children():
            w.destroy()

        fig = Figure(figsize=(8, 5), dpi=100, facecolor=CARD)
        CHARTS[idx][1](fig, self.df)
        try:
            fig.tight_layout(pad=2)
        except Exception:
            pass
        self.canvas = FigureCanvasTkAgg(fig, master=self.canvas_holder)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        tb = NavigationToolbar2Tk(self.canvas, self.tb_holder, pack_toolbar=False)
        tb.config(background=CARD)
        for child in tb.winfo_children():
            try:
                child.config(background=CARD)
            except Exception:
                pass
        tb.update()
        tb.pack(side="left")
        self.toolbar = tb

        if idx == len(CHARTS) - 1 and HAS_PLOTLY:
            self.plotly_btn.pack(side="right", padx=12)
        else:
            self.plotly_btn.pack_forget()

    def open_plotly(self):
        r = top_routes(self.df)
        fig = px.bar(r, x="Bookings", y="Pickup_Location", color="Drop_Location",
                     title="Top 10 Routes", template="plotly_dark")
        path = os.path.join(tempfile.gettempdir(), "pythoncab_top_routes.html")
        fig.write_html(path)
        webbrowser.open("file://" + path)

    # --------------------------------------------------------- analysis ---
    def _page_analysis(self):
        s = self.stats
        info = self.info
        page = tk.Frame(self.body, bg=BG)

        txt = tk.Text(page, bg=CARD, fg=TEXT, relief="flat", font=("Segoe UI", 11),
                      wrap="word", padx=28, pady=22, spacing1=3, spacing3=3,
                      highlightthickness=1, highlightbackground="#22304B",
                      cursor="arrow")
        sb = ttk.Scrollbar(page, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)

        txt.tag_configure("h", foreground=ACCENT, font=("Segoe UI", 14, "bold"),
                          spacing1=16, spacing3=6)
        txt.tag_configure("k", foreground=MUTED)
        txt.tag_configure("v", foreground=TEXT, font=("Segoe UI", 11, "bold"))
        txt.tag_configure("good", foreground=GOOD, font=("Segoe UI", 11, "bold"))
        txt.tag_configure("rec", foreground=TEXT, lmargin1=14, lmargin2=34)
        txt.tag_configure("num", foreground=ACCENT, font=("Segoe UI", 11, "bold"))
        txt.tag_configure("para", foreground="#C7D0E0", lmargin1=4, lmargin2=4,
                          spacing3=6)

        def head(t):
            txt.insert("end", t + "\n", "h")

        def row(k, v, tag="v"):
            txt.insert("end", f"{k}:  ", "k")
            txt.insert("end", f"{v}\n", tag)

        head("🧹  Data cleaning summary")
        row("Original shape", f"{info['raw_shape'][0]} rows × {info['raw_shape'][1]} columns")
        row("Duplicate rows removed", info["duplicates"])
        row("Shape after cleaning", f"{info['clean_shape'][0]} rows × {info['clean_shape'][1]} columns")
        miss = info["missing"]
        miss = miss[miss > 0]
        row("Missing values filled",
            ", ".join(f"{k} ({v})" for k, v in miss.items()) if len(miss) else "none")

        head("🧠  Final analysis")
        row("Top vehicle type", s["top_vehicle"])
        row("Top pickup location", s["top_pickup"])
        row("Top drop location", s["top_drop"])
        row("Most used payment method", s["top_payment"])
        row("Busiest hour", f"{s['busiest_hour']:02d}:00")
        row("Highest-revenue vehicle", s["top_rev_vehicle"])
        row("Highest-revenue month", s["top_rev_month"])
        row("Average fare", f"₹{s['avg_fare']:,.2f}")
        row("Average rating", f"{s['avg_rating']:.2f}")
        row("Distance–fare correlation", f"{s['corr']:.2f}")
        row("Completion rate", f"{s['completion']:.2f} %", "good")

        head("✅  Recommendations")
        for i, r in enumerate(RECOMMENDATIONS, 1):
            txt.insert("end", f"{i}.  ", ("rec", "num"))
            txt.insert("end", r + "\n", "rec")

        head("📌  Project conclusion")
        txt.insert("end", CONCLUSION + "\n", "para")

        txt.config(state="disabled")
        return page


if __name__ == "__main__":
    CabApp().mainloop()