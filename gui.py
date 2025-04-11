import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from PIL import Image, ImageTk
import numpy as np
from arbitrage import BybitArbitrage
import logging

class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 로거 설정
        self.logger = logging.getLogger('TradingApp')
        self.logger.setLevel(logging.INFO)
        
        # 파일 핸들러
        file_handler = logging.FileHandler('trading_gui.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 포맷터
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 핸들러 추가
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 기본 설정
        self.title("Bybit Arbitrage Pro")
        self.geometry("1200x700")  # 창 크기 축소
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # 변수 초기화
        self.arbitrage = BybitArbitrage()
        self.spread_history = []
        self.time_history = []
        self.is_trading = False
        self.total_profit = 0
        self.trade_count = 0
        self.successful_trades = 0
        self.failed_trades = 0
        
        # GUI 구성
        self.setup_gui()
        
        # API 연결 확인 (GUI 구성 후 실행)
        self.after(1000, self.check_api_connection)

    def check_api_connection(self):
        """API 연결 상태 확인"""
        try:
            if not self.arbitrage.test_connection():
                messagebox.showerror("연결 실패", 
                    "Bybit API 연결에 실패했습니다.\n"
                    "인터넷 연결과 API 키를 확인해주세요.")
                return
            
            balance = self.arbitrage.get_wallet_balance()
            if balance:
                messagebox.showinfo("연결 성공", 
                    f"API 연결 성공!\n"
                    f"총 자산: {balance['total']:,.2f} USDT\n"
                    f"사용 가능: {balance['available']:,.2f} USDT")
                
                # 데이터 업데이트 시작
                self.update_data()
            else:
                messagebox.showwarning("잔고 확인 실패", 
                    "지갑 잔고를 가져오는데 실패했습니다.\n"
                    "API 권한을 확인해주세요.")
                
        except Exception as e:
            messagebox.showerror("연결 오류", f"API 연결 오류: {str(e)}")

    def setup_gui(self):
        # 메인 컨테이너
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 상단 패널 (잔고 & 가격 정보)
        self.setup_top_panel(main_container)
        
        # 중앙 패널 (차트 & 거래 내역)
        self.setup_center_panel(main_container)
        
        # 하단 패널 (거래 설정 & 컨트롤)
        self.setup_bottom_panel(main_container)

    def setup_top_panel(self, parent):
        top_frame = ctk.CTkFrame(parent)
        top_frame.pack(fill="x", pady=(0, 5))
        
        # 잔고 정보
        balance_frame = ctk.CTkFrame(top_frame)
        balance_frame.pack(side="left", fill="x", expand=True, padx=5)
        
        self.balance_label = ctk.CTkLabel(balance_frame, text="총 자산: -- USDT", 
                                        font=("Roboto", 14, "bold"))
        self.balance_label.pack(side="left", padx=10)
        
        self.available_label = ctk.CTkLabel(balance_frame, text="거래가능: -- USDT",
                                          font=("Roboto", 14))
        self.available_label.pack(side="left", padx=10)
        
        # 현재 가격 정보
        price_frame = ctk.CTkFrame(top_frame)
        price_frame.pack(side="right", fill="x", expand=True, padx=5)
        
        self.spot_label = ctk.CTkLabel(price_frame, text="현물: -- USDT",
                                      font=("Roboto", 14))
        self.spot_label.pack(side="left", padx=10)
        
        self.futures_label = ctk.CTkLabel(price_frame, text="선물: -- USDT",
                                        font=("Roboto", 14))
        self.futures_label.pack(side="left", padx=10)
        
        self.spread_label = ctk.CTkLabel(price_frame, text="스프레드: --%",
                                       font=("Roboto", 14, "bold"))
        self.spread_label.pack(side="left", padx=10)

    def setup_center_panel(self, parent):
        center_frame = ctk.CTkFrame(parent)
        center_frame.pack(fill="both", expand=True, pady=5)
        
        # 차트 (크기 축소)
        chart_frame = ctk.CTkFrame(center_frame)
        chart_frame.pack(side="left", fill="both", expand=True)
        
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # 거래 내역
        history_frame = ctk.CTkFrame(center_frame)
        history_frame.pack(side="right", fill="both", padx=(5,0))
        
        ctk.CTkLabel(history_frame, text="거래 내역", 
                    font=("Roboto", 14, "bold")).pack(pady=5)
        
        # 거래 내역 테이블
        columns = ('시간', '유형', '수량', '현물가격', '선물가격', '스프레드', '수수료', '수익')
        self.trade_tree = ttk.Treeview(history_frame, columns=columns, 
                                      show='headings', height=10)
        
        # 컬럼 설정
        widths = [70, 80, 70, 90, 90, 80, 70, 70]
        for col, width in zip(columns, widths):
            self.trade_tree.heading(col, text=col)
            self.trade_tree.column(col, width=width)
        
        # 스크롤바 추가
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", 
                                command=self.trade_tree.yview)
        self.trade_tree.configure(yscrollcommand=scrollbar.set)
        
        self.trade_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_bottom_panel(self, parent):
        bottom_frame = ctk.CTkFrame(parent)
        bottom_frame.pack(fill="x", pady=(5,0))
        
        # 거래 설정
        settings_frame = ctk.CTkFrame(bottom_frame)
        settings_frame.pack(side="left", fill="x", expand=True)
        
        # 코인 선택 콤보박스
        self.coin_var = ctk.StringVar(value="BTCUSDT")
        coin_label = ctk.CTkLabel(settings_frame, text="코인:")
        coin_label.pack(side="left", padx=5)
        
        coin_combo = ctk.CTkComboBox(
            settings_frame, 
            values=["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"],
            variable=self.coin_var,
            command=self.on_coin_change
        )
        coin_combo.pack(side="left", padx=5)
        
        # 최소 주문 금액 표시
        self.min_order_label = ctk.CTkLabel(
            settings_frame, 
            text="최소 주문 금액: 10 USDT"
        )
        self.min_order_label.pack(side="left", padx=5)
        
        # 거래량 입력
        amount_label = ctk.CTkLabel(settings_frame, text="거래량:")
        amount_label.pack(side="left", padx=5)
        
        self.amount_var = ctk.StringVar(value="0.001")
        amount_entry = ctk.CTkEntry(
            settings_frame, 
            textvariable=self.amount_var,
            width=100
        )
        amount_entry.pack(side="left", padx=5)
        
        # 거래 통계
        stats_frame = ctk.CTkFrame(bottom_frame)
        stats_frame.pack(side="right", fill="x", expand=True)
        
        self.trades_label = ctk.CTkLabel(stats_frame, 
                                       text="총 거래: 0 | 수익: 0.00 USDT",
                                       font=("Roboto", 12, "bold"))
        self.trades_label.pack(side="left", padx=10)
        
        # 거래 버튼
        self.start_button = ctk.CTkButton(bottom_frame, text="거래 시작", 
                                        command=self.start_trading,
                                        width=100, height=32)
        self.start_button.pack(side="right", padx=5)
        
        self.stop_button = ctk.CTkButton(bottom_frame, text="거래 중지", 
                                       command=self.stop_trading,
                                       width=100, height=32,
                                       fg_color="#FF3B30",
                                       state="disabled")
        self.stop_button.pack(side="right", padx=5)

    def on_coin_change(self, choice):
        """코인 변경 시 호출되는 함수"""
        self.logger.info(f"Selected coin changed to: {choice}")
        # 거래 중지
        if self.is_trading:
            self.stop_trading()
        
        # 차트 초기화
        self.spread_history = []
        self.time_history = []
        self.update_chart()

    def update_data(self):
        """데이터 업데이트"""
        if not hasattr(self, 'arbitrage'):
            return
        
        try:
            symbol = self.coin_var.get()
            
            # 잔고 업데이트
            balance = self.arbitrage.get_wallet_balance()
            if balance:
                self.balance_label.configure(
                    text=f"총 자산: {balance['total']:,.2f} USDT")
                self.available_label.configure(
                    text=f"거래가능: {balance['available']:,.2f} USDT")
            
            # 가격 정보 업데이트
            spot_price = self.arbitrage.get_market_price(symbol, "spot")
            futures_price = self.arbitrage.get_market_price(symbol, "linear")
            
            if spot_price and futures_price:
                self.spot_label.configure(
                    text=f"현물: {spot_price:,.2f}")
                self.futures_label.configure(
                    text=f"선물: {futures_price:,.2f}")
                
                spread = (futures_price - spot_price) / spot_price * 100
                self.spread_label.configure(
                    text=f"스프레드: {spread:.3f}%")
                
                # 스프레드 히스토리 업데이트
                self.spread_history.append(spread)
                self.time_history.append(datetime.now())
                
                if len(self.spread_history) > 50:
                    self.spread_history.pop(0)
                    self.time_history.pop(0)
                
                self.update_chart()
                
                # 거래 중이면 새로운 거래 실행
                if self.is_trading:
                    self.execute_single_trade()
        
        except Exception as e:
            self.logger.error(f"Data update error: {str(e)}")
        
        # 1초 후 다시 업데이트
        self.after(1000, self.update_data)

    def add_trade_to_history(self, trade_result):
        """거래 내역 추가"""
        try:
            self.trade_tree.insert('', 0, values=(
                trade_result['timestamp'],
                trade_result['type'],
                f"{trade_result['amount']:.6f}",
                f"{trade_result['spot_price']:.2f}",
                f"{trade_result['futures_price']:.2f}",
                f"{trade_result['spread']:.3f}%",
                f"{trade_result['profit']:.2f}"
            ))
        except Exception as e:
            self.logger.error(f"Error adding trade to history: {str(e)}")

    def update_trade_stats(self, trade_result):
        """거래 통계 업데이트"""
        try:
            self.trade_count += 1
            self.total_profit += trade_result['profit']
            
            if trade_result['profit'] > 0:
                self.successful_trades += 1
            
            win_rate = (self.successful_trades / self.trade_count * 100) if self.trade_count > 0 else 0
            
            self.trades_label.configure(text=(
                f"총 거래: {self.trade_count} | "
                f"성공: {self.successful_trades} | "
                f"승률: {win_rate:.1f}% | "
                f"총 수익: {self.total_profit:.2f} USDT"
            ))
        except Exception as e:
            self.logger.error(f"Error updating trade stats: {str(e)}")

    def log_message(self, message):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} - {message}")  # 콘솔 출력
        
        # 로그 파일에도 기록
        with open('trading_log.txt', 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} - {message}\n")

    def update_chart(self):
        """차트 업데이트"""
        self.ax.clear()
        self.ax.plot(self.time_history, self.spread_history, 'b-')
        self.ax.set_ylabel('Spread (%)')
        self.ax.grid(True)
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.xticks(rotation=45)
        self.canvas.draw()

    def start_trading(self):
        """거래 시작"""
        try:
            self.is_trading = True
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            
            # 거래 시작 로그
            self.logger.info("=== Trading Started ===")
            self.execute_single_trade()  # 즉시 첫 거래 실행
            
        except Exception as e:
            self.logger.error(f"Start trading error: {str(e)}")
            self.stop_trading()

    def execute_single_trade(self):
        """단일 거래 실행"""
        try:
            symbol = self.coin_var.get()
            
            # 현재 가격 조회
            spot_price = self.arbitrage.get_market_price(symbol, "spot")
            futures_price = self.arbitrage.get_market_price(symbol, "linear")
            
            if not spot_price or not futures_price:
                self.logger.error("Failed to get market prices")
                return
            
            # 스프레드 계산
            spread = (futures_price - spot_price) / spot_price * 100
            self.logger.info(f"Current spread: {spread:.3f}%")
            
            # 거래량 계산 (총 자산의 1%)
            balance = self.arbitrage.get_wallet_balance()
            if not balance:
                self.logger.error("Failed to get wallet balance")
                return
            
            trade_value = balance['total'] * 0.01  # 총 자산의 1%
            trade_amount = trade_value / spot_price
            
            # 거래 실행
            self.logger.info(f"Executing trade - Amount: {trade_amount:.6f} {symbol}")
            result = self.arbitrage.execute_trade(symbol, spot_price, futures_price, trade_amount)
            
            if result:
                self.add_trade_to_history(result)
                self.update_trade_stats(result)
                self.logger.info(f"Trade successful - Profit: {result['profit']:.2f} USDT")
            else:
                self.logger.error("Trade execution failed")
        
        except Exception as e:
            self.logger.error(f"Trade execution error: {str(e)}")

    def stop_trading(self):
        """거래 중지"""
        self.is_trading = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()