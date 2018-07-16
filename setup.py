from setuptools import setup, find_packages

setup(
    name="microservice",
    version="0.2.28",
    description="Powerful REST API microservice on Tornado",
    url="https://git.phobos.work/mbulygin/microservice",
    author="Mikhail Bulygin",
    packages=find_packages(),
    install_requires=[
        "aiopg==0.13.2",
        "oauth2==1.9.0.post1",
        "peewee==2.10.2",
        "peewee-async==0.5.12",
        "prometheus-client==0.3.0",
        "pyTelegramBotAPI==3.6.3",
        "raven==6.9.0",
        "requests==2.18.4",
        "tornado==5.0.2",
        "ua-parser==0.8.0",
        "urllib3==1.22",
        "google-auth==1.5.0",
        "pytz==2018.5",
    ]
)
