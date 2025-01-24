This script automatically clips every coupon available in your Raley's Something Extra account. Raley's has instituted an obnoxious system where self-advertised prices sometimes require that you hunt down and click on a coupon in their website or app. This script clicks all of them for you, so next time you shop you'll have every possible discount. 

It also applies available Something Extra Dollars to your account so you don't have to remember to apply your points each quarter.

## Installation

Node and Python are required on your system. Install the script dependencies with these commands:

```bash
pip3 install playwright asyncio
playwright install
```

## Configuration

Create two environment variables `RALEYS_EMAIL` and `RALEYS_PASSWORD` and set them to your Raley's account email address and password. 

Alternatively, install the Python package `dotenv` (using `pip3 install python-dotenv`) and create a file named `.env` with contents that look like this, with your account email and password after the = signs.

```bash
RALEYS_EMAIL=
RALEYS_PASSWORD=
```

## Running

`python raleys-autoclipper.py`

This application can be run with cron. For example to run it daily, add something to your crontab like this:

`0 0 * * * /usr/bin/python3 /path/to/raleys-autoclippper.py`

## Docker

There's a Dockerfile in this repo that will run the script. It relies on the same environment variables mentioned above. If you have a .env file in the you build the Docker container from, it will use that. Or you can edit the Dockerfile to set the environment varialbles. Or pass them in the `docker run` command or set them in a Docker compose file.

The Docker container will run the script on startup and also contains a cronjob to run it every morning and every evening, US Pacific time. Raley's ads and new coupons tend to come out on Tuesdays, so this will also run every four hours on Tuesday to maximize the chances of picking up new coupons.

Configure an environment variable named `MAIL_TO` in the Dockerfile, in the `.env` file, or on the command line. This email address will receive a daily log from the script.

The Dockerfile fetches the latest version of the script from Github daily so you'll always be up to date.
