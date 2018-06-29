from setuptools import setup, find_packages

setup(
    name="microservice",
    version="0.2.6",
    description="Powerful REST API microservice on Tornado",
    url="https://git.phobos.work/mbulygin/microservice",
    author="Mikhail Bulygin",
    packages=find_packages(),
    install_requires=[
        "aiopg==0.13.2",
        "oauth2==1.9.0.post1",
        "peewee==2.10.2",
        "peewee-async==0.5.10",
        "prometheus-client==0.1.1",
        "pyTelegramBotAPI==3.5.1",
        "raven==6.5.0",
        "requests==2.18.4",
        "tornado==5.0.2",
        "ua-parser==0.7.3",
        "urllib3==1.22",
        "google-auth==1.0.2",
        "pytz==2018.3",
    ]
)
