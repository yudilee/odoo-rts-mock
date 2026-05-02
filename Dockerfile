FROM python:3.10-slim

ENV TZ=UTC

WORKDIR /app
RUN pip install flask gunicorn
COPY app.py .
EXPOSE 5050
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "app:app"]
