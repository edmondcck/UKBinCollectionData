import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)

        # Set up Selenium to run 'headless'
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Create Selenium webdriver
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.npt.gov.uk/2195")

        # Accept cookies banner
        cookieAccept = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, "ccc-notify-accept"))
        )
        cookieAccept.click()

        # Populate postcode field
        inputElement_postcode = driver.find_element(
            By.ID,
            "ContentPlaceHolderDefault_ctl13_nptLLPG2_25_addresslookup_txtTmpPostcode",
        )
        inputElement_postcode.send_keys(user_postcode)

        # Click search button
        findAddress = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, "ContentPlaceHolderDefault_ctl13_nptLLPG2_25_addresslookup_btnFindAddress"))
        )
        findAddress.click()

        time.sleep(1)

        # Wait for the 'Select address' dropdown to appear and select option matching UPRN
        dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, "ContentPlaceHolderDefault_ctl13_nptLLPG2_25_addresslookup_ddlAddressLookup"))
        )
        # Create a 'Select' for it, then select the matching URPN option
        dropdownSelect = Select(dropdown)
        dropdownSelect.select_by_value(user_uprn)

        # Remove back to top button if exists
        driver.execute_script("""
        if (document.contains(document.querySelector(".backtotop"))) {
            document.querySelector(".backtotop").remove();
        }
        """)

        # Wait for the submit button to appear, then click it to get the collection dates
        submit = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ContentPlaceHolderDefault_ctl13_nptLLPG2_25_btnDisplay"))
        )
        submit.click()

        soup = BeautifulSoup(driver.page_source, features="html.parser")

        # Get the property details
        property_details = soup.find(
            "div",
            {"id": "ContentPlaceHolderDefault_ctl13_nptLLPG2_25_divPropertyDetails"}
        )

        # Get the dates
        for date in property_details.find_all("h2"):
            if date.get_text(strip=True) != "Bank Holidays":
                bin_date = datetime.strptime(
                    date.get_text(strip=True).replace('&nbsp', ' ') + " " + datetime.now().strftime("%Y"),
                    "%A, %d %B %Y"
                )
                bin_types_wrapper = date.find_next_sibling("div")
                for bin_type_wrapper in bin_types_wrapper.find_all("div", {"class": "card"}):
                    if bin_date and bin_type_wrapper:
                        bin_type = bin_type_wrapper.find("a").get_text(strip=True)
                        bin_type += " (" + bin_type_wrapper.find("span").get_text(strip=True) + ")"
                        dict_data = {
                            "type": bin_type,
                            "collectionDate": bin_date.strftime(date_format)
                        }
                        data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return data
