import os
import re
import time
import random
import string
import requests
from io import BytesIO
from PIL import Image
import ddddocr
import chromedriver_autoinstaller  # 导入 chromedriver-autoinstaller

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from contextlib import redirect_stdout


# ========= 基础 =========
def rand_str(length=10, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choices(chars, k=length))


def gen_email():
    return f"{rand_str()}@{random.choice(['qq.com', 'outlook.com', 'gmail.com'])}"


def gen_password():
    return rand_str(12, string.ascii_letters + string.digits)


# ========= 验证码处理 =========
class CaptchaSolver:
    def __init__(self):
        # 屏蔽 ddddocr 初始化输出
        with open(os.devnull, "w") as f, redirect_stdout(f):
            self.ocr = ddddocr.DdddOcr(beta=True)

    @staticmethod
    def preprocess(img_bytes):
        """灰度 + 二值化"""
        img = Image.open(BytesIO(img_bytes)).convert("L")
        img = img.point(lambda x: 0 if x < 140 else 255)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def is_valid(code):
        """只允许4位字母+数字"""
        return bool(re.fullmatch(r"[A-Za-z0-9]{4}", code))

    def solve(self, img_bytes):
        processed = self.preprocess(img_bytes)
        code = self.ocr.classification(processed)

        if not self.is_valid(code):
            return None

        return code


# ========= 注册 =========
def register(max_retry=8):
    session = requests.Session()
    solver = CaptchaSolver()

    captcha_url = "https://a.aiguobit.com/users/vcode"
    register_url = "https://a.aiguobit.com/users/register"

    for attempt in range(1, max_retry + 1):
        img_bytes = session.get(captcha_url).content

        code = solver.solve(img_bytes)

        if not code:
            print(f"[{attempt}] 验证码格式非法，跳过")
            continue

        print(f"[{attempt}] 验证码识别: {code}")

        email = gen_email()
        password = gen_password()

        resp = session.post(register_url, data={
            "email": email,
            "password": password,
            "password2": password,
            "checkcode": code
        })

        text = resp.text

        if resp.status_code == 200 and "错误" not in text:
            print(f"注册成功: {email}")
            return email, password

        if "验证码错误" in text:
            print(f"[{attempt}] 验证码错误")
        else:
            print(f"[{attempt}] 注册失败")

        time.sleep(1)

    raise RuntimeError("注册失败（多次重试）")


# ========= 浏览器 =========
def init_driver():
    # 自动安装与 Chrome 版本匹配的 chromedriver
    chromedriver_autoinstaller.install()

    options = Options()
    options.add_argument("--headless")  # 必须启用无头模式
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    return webdriver.Chrome(options=options)


# ========= 登录 =========
def login(driver, email, password):
    driver.get("https://a.aiguobit.com/users/ucenter")

    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(email)
    driver.find_element(By.NAME, "password").send_keys(password + "\n")

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))


# ========= 领取试用 =========
def claim_trial(driver):
    wait = WebDriverWait(driver, 30)
    driver.get("https://a.aiguobit.com/users/ucenter")

    try:
        btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'领取')]")
        ))
        btn.click()
        time.sleep(2)
    except:
        pass


# ========= 获取订阅链接 =========
def get_sub_link(driver):
    wait = WebDriverWait(driver, 10)
    driver.get("https://a.aiguobit.com/users/ucenter")

    btn = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//div[contains(text(),'视频秒开订阅')]")
    ))

    onclick = btn.get_attribute("onclick")
    match = re.search(r"copyText\('(.*?)'\)", onclick)

    if not match:
        raise RuntimeError("订阅链接解析失败")

    return match.group(1)


# ========= 下载并重命名订阅文件 =========
def download_subscription_file(link):
    # 发送 GET 请求下载 YAML 文件
    response = requests.get(link)

    # 检查请求是否成功
    if response.status_code == 200:
        # 将下载的内容保存为 Subscription.yaml
        with open("Subscription.yaml", "wb") as file:
            file.write(response.content)
        print("Subscription.yaml has been downloaded and saved.")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")


# ========= 下载并重命名第二个订阅文件 =========
def download_second_subscription_file(link):
    # 去掉链接中的查询字符串（问号及其后面部分）
    clean_link = link.split('?')[0]

    # 发送 GET 请求下载 YAML 文件
    response = requests.get(clean_link)

    # 检查请求是否成功
    if response.status_code == 200:
        # 将下载的内容保存为 Subscription2.yaml
        with open("Subscription2.yaml", "wb") as file:
            file.write(response.content)
        print("Subscription2.yaml has been downloaded and saved.")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")


# ========= 主流程 =========
def main():
    email, password = register()

    driver = init_driver()

    try:
        login(driver, email, password)
        claim_trial(driver)

        link = get_sub_link(driver)
        print("\n订阅链接：")
        print(link)

        # 下载并重命名为 Subscription.yaml
        download_subscription_file(link)

        # 下载第二个订阅文件并重命名为 Subscription2.yaml
        download_second_subscription_file(link)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
