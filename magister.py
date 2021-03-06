if __name__ == "__main__":
    print("this file is a library.\nthis file is not meant to be run.")
    exit(1)

import itertools
import platform
import sys
from os import getcwd, system
from os.path import isfile, join
from time import sleep

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Chrome, ChromeOptions, Firefox, FirefoxOptions, Opera
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config

running_windows = platform.system() == "Windows"

DRIVER = join(getcwd(), config.BROWSER)


class DriverNotFoundError(Exception):
    pass


class Cijfer:
    def __init__(self, vak, date, description, cijfer, weging, inhalen) -> None:
        self.vak = vak
        self.date = date
        self.description = description
        self.cijfer = cijfer
        self.weging = weging
        self.inhalen = inhalen

        if cijfer == "O" or cijfer == "T" or cijfer == "V" or cijfer == "G":
            self.type = "werkhouding"
        elif cijfer == "Inh":
            self.type = "inhalen"
        else:
            self.type = "cijfer"

    @property
    def all(self):
        return {
            'vak': self.vak,
            'desc': self.description,
            'cijfer': self.cijfer,
            'weging': self.weging,
            'date': self.date,
            'inh': self.inhalen,
            'type': self.type
        }

    @property
    def simple(self):
        return [self.vak, self.cijfer, self.weging, self.date]


def log(type: str, msg: str):
    print("\033[92m{0} :\033[0m {1}".format(type, msg))


class Magister:
    def __init__(self) -> None:
        system("cls||clear")
        self.nobrowser = not config.WINDOW_VISIBLE

        log("INFO", f"nobrowser = {self.nobrowser}")

        self.school = config.SCHOOL
        self.logindata = config.LOGIN

        if not isfile(DRIVER):
            raise DriverNotFoundError("ERROR: driver needs to be in folder.")

        log("INFO", '[driver path] = "{}"'.format(DRIVER))
        log("INFO", "starting client...")
        if config.BROWSER.startswith("geckodriver"):
            self.opts = FirefoxOptions()
            self.opts.headless = self.nobrowser

            self.driver = Firefox(options=self.opts, executable_path=DRIVER)
        elif config.BROWSER.startswith("operadriver"):
            self.opts = ChromeOptions()

            self.opts.binary_location = config.Locations.operaGX

            # NOTE --headless is not supported by opera

            self.opts.add_argument("--disable-gpu")
            self.opts.add_argument("--log-level=3")
            self.opts.add_argument("--silent")
            self.opts.add_experimental_option("w3c", True)
            self.opts.binary_location = config.Locations.operaGX

            self.driver = Opera(options=self.opts, executable_path=DRIVER)
        else:
            self.opts = ChromeOptions()
            if self.nobrowser:
                self.opts.add_argument("--headless")
            self.opts.add_argument("--log-level=3")
            self.opts.add_argument("--silent")
            self.driver = Chrome(options=self.opts, executable_path=DRIVER)

        

        print("\n\033[93mloading login page...", end="\033[92m")
        sleep(0.3)

    def login(self):
        username, password = self.logindata

        self.driver.get(f"https://{self.school}.magister.net")

        if (
            config.BROWSER.startswith("operadriver")
            and len(self.driver.window_handles) > 1
        ):
            self.driver.switch_to.window(self.driver.window_handles[-1])  # switch tabs

        WebDriverWait(self.driver, 6).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        print("done.\033[0m")

        print("\n\033[93mlogging in...", end="\033[92m")

        self.driver.find_element(By.ID, "username").send_keys(username)
        self.driver.find_element(By.ID, "username_submit").click()
        WebDriverWait(self.driver, 6).until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.ID, "password_submit").click()

        print("done.\033[0m")

        print("\n\033[93mloading home page (this may take a while)...", end="\033[92m")

        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.ID, "menu-vandaag"))
        )

        print("done.\033[0m")
        """ login successful """

    def agenda_items(self) -> list[dict]:
        self.go_agenda()
        items = []

        agenda = self.driver.find_elements(By.TAG_NAME, 'tr')
        agenda_ch = [agenda[i:i+3] for i in range(0, len(agenda))]
        for i, _ in enumerate(agenda_ch):
            agenda_ch[i] = [x.text for x in agenda_ch[i] if x.text != ""]
        
        # NOTE work in progress
        # TODO
        for dag in agenda_ch:
            if dag == []:
                continue
            try:
                desc = dag[1].replace("  \nHuiswerk", "").split('\n')[2]
            except IndexError:
                desc = ""
            vak = dag[1].split('\n')[1]
            tijd = dag[1].split('\n')[0]
            items.append(
                {
                    'dag': dag[0],
                    'tijd': tijd,
                    'vak': vak,
                    'desc': desc
                }
            )

        
        return items


    def go_home(self):
        WebDriverWait(self.driver, 6).until(
            EC.presence_of_element_located((By.ID, "menu-vandaag"))
        )
        self.driver.find_element_by_id("menu-vandaag").click()
        log("INFO", "went to homepage")

    def go_agenda(self):
        WebDriverWait(self.driver, 6).until(
            EC.presence_of_element_located((By.ID, "menu-agenda"))
        )
        self.driver.find_element_by_id("menu-agenda").click()
        
        sleep(1.5)
        log("INFO", "went to agenda page")

    def go_leermiddelen(self):
        WebDriverWait(self.driver, 6).until(
            EC.presence_of_element_located((By.ID, "menu-leermiddelen"))
        )
        self.driver.find_element_by_id("menu-leermiddelen").click()
        log("INFO", "went to leermiddelen page")

    def leermiddelen(self) -> dict:
        self.go_leermiddelen()

        for second in range(1, 6):
            print(
                "\033[92mINFO :\033[0m waiting for leermiddelen to load... [{}/5]".format(
                    second
                ),
                end="\r",
            )
            sleep(1)
        print()

        result = [i.text for i in self.driver.find_elements_by_tag_name("td")]

        if not result:
            log("INFO", "no leermiddelen found.")
            return

        leermiddelen = [
            list(y)
            for x, y in itertools.groupby(result, lambda z: z == "Digitaal")
            if not x
        ]
        for (i, _j) in enumerate(leermiddelen):
            leermiddelen[i] = [x for x in leermiddelen[i] if x != ""]

        leermiddelen_dict = []

        # TODO fix links not working in leermiddelen_dict

        for _, item in enumerate(leermiddelen):
            if len(item) != 3:
                continue
            leermiddelen_dict.append(
                {
                    "vak": item[0],
                    "titel": item[1],
                    "url": self.driver.find_elements_by_tag_name("a")(
                        item[1]
                    ).get_attribute("href"),
                    "ean": item[2],
                }
            )

        return leermiddelen_dict

    def cijfers(self) -> list[Cijfer]:
        """
        retrieve the list of all the latest grades in the 'cijfers' section on the magister homepage.
        """

        WebDriverWait(self.driver, 6).until(
            EC.presence_of_element_located((By.ID, "menu-cijfers"))
        )
        self.driver.find_element_by_id("menu-cijfers").click()
        log("INFO", "went to 'cijfers'")

        WebDriverWait(self.driver, 6).until(
            EC.presence_of_element_located((By.TAG_NAME, "td"))
        )

        cijfers = []
        sleep(0.4)

        result = [i.text for i in self.driver.find_elements_by_tag_name("td")]

        if config.BROWSER.startswith("chromedriver") or config.BROWSER.startswith(
            "operadriver"
        ):
            cijfers_spl = [
                list(y)
                for x, y in itertools.groupby(result, lambda z: z == " ")
                if not x
            ]
        else:
            cijfers_spl = [
                list(y)
                for x, y in itertools.groupby(result, lambda z: z == "")
                if not x
            ]
        """
        order: [vak, date, description, cijfer, weging]
        dict return:
            {
                "vak": i[0],
                "date": i[1],
                "description": i[2],
                "cijfer": i[3],
                "weging": i[4],
                "inhalen": i[3] == "Inh"
            }
        """
        for i in cijfers_spl:
            c = Cijfer(i[0], i[1], i[2], i[3].replace(",", "."), i[4], i[3] == "Inh")
            cijfers.append(c)

        return cijfers

    def cijfers_all(self):
        # NOTE work in progress

        WebDriverWait(self.driver, 6).until(
            EC.presence_of_element_located((By.ID, "menu-cijfers"))
        )
        self.driver.find_element_by_id("menu-cijfers").click()
        log("INFO", "went to 'cijfers'")

        WebDriverWait(self.driver, 6).until(
            EC.presence_of_element_located((By.TAG_NAME, "dna-button"))
        )
        self.driver.find_element_by_tag_name("dna-button").click()
        log("INFO", "went to 'cijfers uitgebreid'")

        WebDriverWait(self.driver, 6).until(
            EC.presence_of_element_located((By.TAG_NAME, "th"))
        )

        """ loaded uitgebreide cijfers """

        # TODO implement

    def stop(self):
        log("INFO", "stopping driver...")
        self.driver.quit()
        sys.exit(0)
