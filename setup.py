from setuptools import setup, find_packages

setup(
    name="microservice",
    version="0.3.3",
    description="Powerful REST API microservice on Tornado",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/pasaranax/microservice",
    author="Mikhail Bulygin",
    author_email="pasaranax@gmail.com",
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)'
    ],
    install_requires=[
        "aiopg==0.13.2",
        "oauth2==1.9.0.post1",
        "peewee==2.10.2",
        "peewee-async==0.5.12",
        "prometheus-client==0.3.0",
        "pyTelegramBotAPI==3.6.5",
        "raven==6.9.0",
        "requests==2.18.4",
        "tornado==5.1",
        "ua-parser==0.8.0",
        "urllib3==1.22",
        "google-auth==1.5.0",
        "pytz==2018.5",
        "aioredis==1.1.0",
    ]
)
