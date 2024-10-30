from api import generate_cogview_image
from dotenv import load_dotenv
load_dotenv()


def cogview_example():
    image_prompt = "鸟山明漫画风格，孤舟蓑笠翁，独钓寒江雪"
    image_url = generate_cogview_image(image_prompt)

    print("image_prompt:")
    print(image_prompt)
    print("image_url:")
    print(image_url)


if __name__ == "__main__":
    cogview_example()
