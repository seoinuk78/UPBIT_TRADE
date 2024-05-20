import os
import sys
import time
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from dotenv import load_dotenv
from pytz import timezone
import pyupbit

# 환경 변수 로드
load_dotenv()

# 실행 파일명 추출
script_name = os.path.basename(sys.argv[0])
coin_name = script_name.split('.')[0]

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_filename = script_name.replace(".py", ".log")
handler = TimedRotatingFileHandler(log_filename, when="M", interval=5, backupCount=3, encoding='utf-8', utc=False)
handler.setFormatter(logging.Formatter('%(asctime)s,%(msecs)03d [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
handler.tz = timezone('Asia/Seoul')  # 타임존을 Asia/Seoul로 설정
logger.addHandler(handler)

# Upbit 클라이언트 객체 생성
access_key = os.getenv("UPBIT_ACCESS_KEY")
secret_key = os.getenv("UPBIT_SECRET_KEY")
upbit = pyupbit.Upbit(access_key, secret_key)

# 스토캐스틱 RSI 설정값
RSI_PERIOD = 14
SMOOTH_K = 3
SMOOTH_D = 3

def calculate_stochastic_rsi(series, period=14, smooth_k=3, smooth_d=3):
    # RSI 계산
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Stochastic RSI 계산
    rsi_min = rsi.rolling(window=period).min()
    rsi_max = rsi.rolling(window=period).max()
    stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min) * 100
    stoch_rsi_k = stoch_rsi.rolling(window=smooth_k).mean()
    stoch_rsi_d = stoch_rsi_k.rolling(window=smooth_d).mean()
    return stoch_rsi_k, stoch_rsi_d

def is_oversold(k, d, threshold=20):
    # %K와 %D가 모두 과매도 상태인지 확인
    return k < threshold and d < threshold

def is_cross_up(k, d):
    # %K가 %D를 상향 돌파하는지 확인
    return k.iloc[-1] > d.iloc[-1] and k.iloc[-2] <= d.iloc[-2]

def get_holding_coin_balance(coin_name):
    # 보유 중인 코인의 잔고 수량 확인
    balance = upbit.get_balance(coin_name)
    return balance

def trade(coin_name):
    # 보유 중인 코인의 잔고 수량 확인
    coin_balance = get_holding_coin_balance(coin_name)

    # 매수 대상인 코인이 이미 보유 중인 경우 조치 수행
    if coin_balance == 0:
        # 현재 시간
        now = datetime.now()

        # 스토캐스틱 RSI 계산
        try:
            ohlcv = pyupbit.get_ohlcv(f"KRW-{coin_name}", interval="minute1")
            if ohlcv is not None:
                stoch_rsi_k, stoch_rsi_d = calculate_stochastic_rsi(ohlcv['close'], RSI_PERIOD, SMOOTH_K, SMOOTH_D)

                # 매수 조건: %K가 %D를 상향 돌파하고 %K와 %D가 모두 과매도 상태일 때 매수
                if is_cross_up(stoch_rsi_k, stoch_rsi_d) and is_oversold(stoch_rsi_k.iloc[-1], stoch_rsi_d.iloc[-1]):
                    logging.info(f"{coin_name} - 스토캐스틱 RSI K: {stoch_rsi_k.iloc[-1]:.2f}, 스토캐스틱 RSI D: {stoch_rsi_d.iloc[-1]:.2f}")
                    # 매수 주문
                    upbit.buy_market_order(f"KRW-{coin_name}", 10000)  # 시장가 매수 주문, 주문 총액(KRW)=10,000원
                    logging.info(f"{coin_name} 매수 주문 완료")
                else:
                    logging.info(f"{coin_name} - 스토캐스틱 RSI K: {stoch_rsi_k.iloc[-1]:.2f}, 스토캐스틱 RSI D: {stoch_rsi_d.iloc[-1]:.2f}, 매수 조건 미달")
            else:
                logging.error(f"OHLCV 데이터를 불러올 수 없습니다: KRW-{coin_name}")
        except Exception as e:
            logging.error(f"에러 발생: {str(e)}")
    else:
        logging.info(f"{coin_name}은(는) 이미 보유 중인 코인입니다. 매수하지 않습니다.")

if __name__ == "__main__":
    coins = [coin_name]  # 실행 파일명을 매매 대상으로 사용
    while True:
        for coin in coins:
            trade(coin)
            time.sleep(10)  # 10초마다 평가
