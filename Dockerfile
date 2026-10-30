FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN mkdir -p /app/runtime && chown -R 10001:10001 /app
USER 10001
ENTRYPOINT ["python"]
CMD ["-m", "copilot.server", "--host", "0.0.0.0"]
