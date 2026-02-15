# 1. 파이썬 3.11 슬림 버전 (가볍고 빠름)
FROM python:3.11-slim

# 2. 파이썬 로그가 터미널에 바로 찍히게 설정 (디버깅 필수)
ENV PYTHONUNBUFFERED=1

# 3. 작업 폴더 생성
WORKDIR /app

# 4. 필수 시스템 패키지 설치 (PostgreSQL 연결용 라이브러리 등)
# -y: 질문에 다 yes라고 대답
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. 내 컴퓨터의 requirements.txt를 도커 안으로 복사
COPY requirements.txt /app/

# 6. 패키지 설치 (pip 업그레이드 후 설치)
RUN pip install --upgrade pip && pip install -r requirements.txt

# 7. 프로젝트 코드 전체를 도커 안으로 복사
COPY . /app/

# 8. 포트 8000번 열기
EXPOSE 8000

# 9. 서버 실행 명령어 (gunicorn 사용)
# config.wsgi:application -> config 폴더 안의 wsgi.py를 실행하라는 뜻
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]