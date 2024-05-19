import os
import sys
import time
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
import pyupbit

# 환경 변수 로드
load_dotenv()

# 실행 파일명 추출 및 로깅 설정
script_name = os.path.basename(sys.argv[0])
log_filename = script_name.replace(".py", ".log")
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(log_filename, when="M", interval=5, backupCount=12, encoding='utf-8', utc=True)
handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(handler)

# Upbit 클라이언트 객체 생성
access_key = os.getenv("UPBIT_ACCESS_KEY")
secret_key = os.getenv("UPBIT_SECRET_KEY")
upbit = pyupbit.Upbit(access_key, secret_key)

# 매도 이익 임계값 및 손절 임계값 설정 (100% = 1.00, 10% = 0.10, 1% = 0.01, 0.1% = 0.001,0.01% = 0.0001)
sell_profit_threshold = 0.0025  # 0.25%
stop_loss_threshold = -0.0025  # -0.25%

def log_previous_execution():
    """ 로그 기록 및 초기 실행 체크 """
    if not hasattr(log_previous_execution, "first_execution"):
        log_previous_execution.first_execution = True

    if log_previous_execution.first_execution:
        logger.info("First execution at {}".format(datetime.now()))
        log_previous_execution.first_execution = False

def log_coin_balances():
    """ 코인 잔고 로깅 """
    balances = upbit.get_balances()
    if not isinstance(balances, list):  # 반환된 데이터가 리스트인지 확인
        logger.error(f"Expected list, got {type(balances)}: {balances}")
        return
    for balance in balances:
        if not isinstance(balance, dict):  # 각 항목이 딕셔너리인지 확인
            logger.error(f"Expected dict, got {type(balance)}: {balance}")
            continue
        try:
            currency = balance['currency']
            if currency in ["KRW", "USDT"]:  # KRW와 USDT는 기록하지 않음
                continue
            coin_name = "KRW-" + currency
            avg_buy_price = float(balance.get('avg_buy_price', 0))
            balance_amount = float(balance.get('balance', 0))
            log_message = f"{coin_name} 보유량: {balance_amount}, 매수평균가: {avg_buy_price}"
            logger.info(log_message)
        except TypeError as e:
            logger.error(f"TypeError accessing balance data: {balance} - {str(e)}")
        except Exception as e:
            logger.error(f"An error occurred processing balance data: {balance} - {str(e)}")


def sell_coins(upbit, sell_profit_threshold, stop_loss_threshold):
    """ 매도 실행 조건 검사 및 매도 주문 """
    balances = upbit.get_balances()
    for balance in balances:
        currency = balance['currency']
        if currency in ["KRW", "USDT"]:  # KRW와 USDT는 매도 대상에서 제외
            continue

        coin = "KRW-" + currency
        current_price = pyupbit.get_current_price(coin)
        if not current_price:
            logger.error(f"Failed to fetch current price for {coin}")
            continue

        avg_buy_price = float(balance['avg_buy_price'])
        current_balance = float(balance['balance'])

        if current_price >= avg_buy_price * (1 + sell_profit_threshold) or current_price <= avg_buy_price * (1 + stop_loss_threshold):
            response = upbit.sell_market_order(coin, current_balance)
            if 'error' in response:
                logger.error(f"Failed to sell {coin}: {response['error']['message']}")
            else:
                logger.info(f"Sold {coin} at {datetime.now()}, result: {response}")

try:
    while True:
        log_previous_execution()
        log_coin_balances()
        sell_coins(upbit, sell_profit_threshold, stop_loss_threshold)  # 필요한 인자들을 전달
        time.sleep(2)
except KeyboardInterrupt:
    logger.info("Script interrupted by user.")
except Exception as e:
    logger.error(f"An unexpected error occurred: {str(e)}")