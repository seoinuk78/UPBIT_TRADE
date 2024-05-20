import os
import glob
import time

def delete_old_log_files(directory):
    """
    directory: 삭제할 로그 파일이 있는 디렉토리 경로
    """
    # 디렉토리에서 확장자가 .log.인 파일 목록을 가져옵니다.
    files = glob.glob(os.path.join(directory, "*.log.*"))

    # 파일들을 순회하면서 삭제합니다.
    for file in files:
        os.remove(file)

# 삭제할 로그 파일이 있는 디렉토리 경로를 설정합니다.
log_directory = "/home/ubuntu/01_UPBIT_ALL_SELL_ORDER"

# 주기적으로 파일을 삭제합니다.
while True:
    # delete_old_log_files 함수를 호출하여 .log. 확장자인 파일을 삭제합니다.
    delete_old_log_files(log_directory)
    # 2분마다 실행합니다.
    time.sleep(60)  # 1분은60 초입니다.