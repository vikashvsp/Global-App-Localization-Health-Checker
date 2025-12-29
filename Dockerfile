FROM apify/actor-python:3.11

COPY requirements.txt ./
RUN pip install -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

COPY . ./

CMD ["python3", "-m", "src.main"]
