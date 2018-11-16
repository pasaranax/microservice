from setuptools import setup, find_packages

setup(
    name="microservice",
    version="0.3.12",
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
        "aiopg>=0.13.2,<1",
        "oauth2>=1.9.0.post1,<1.10",
        "peewee>=2.10.2,<3",
        "peewee-async>=0.5.12,<0.6",
        "prometheus-client>=0.3.0,<1",
        "pyTelegramBotAPI>=3.6.5,<3.7",
        "raven>=6.9.0,<6.10",
        "requests>=2.19,<3",
        "tornado>=5.1,<6",
        "ua-parser>=0.8.0,<1",
        "urllib3>=1.22,<2",
        "google-auth>=1.5.0,<1.6",
        "pytz>=2018.5",
        "aioredis>=1.1.0,<2",
        "asgiref>=2.3.2,<2.4"
    ]
)
