# 1. 파이썬 3.11 슬림 버전
FROM python:3.11-slim

# 2. 파이썬 로그가 터미널에 바로 찍히게 설정
ENV PYTHONUNBUFFERED=1

# 3. 작업 폴더 생성
WORKDIR /app

# 4. 필수 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. requirements.txt 복사 및 설치
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# 6. 소스 코드 복사
COPY . /app/

# 7. 정적 파일 모으기 (이 줄 추가! ⭐)
# (주의: settings.py에 STATIC_ROOT 설정이 있어야 함)
RUN python manage.py collectstatic --noinput

# 8. 포트 8000번 열기
EXPOSE 8000

# 9. 서버 실행
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]