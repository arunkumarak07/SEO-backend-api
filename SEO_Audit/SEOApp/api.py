from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from bs4 import BeautifulSoup
import pandas as pd
from collections import Counter
import datetime
import ssl
import socket
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

class SEOAuditAPI(APIView):
    def post(self, request):
        website_url = request.data.get('url')
        keywords = request.data.get('keyword')
        response_data = {"website":website_url}

        # 1. Check for robots.txt
        def check_robots_txt(website_url):
            robots_url = f"{website_url}/robots.txt"
            try:
                response = requests.get(robots_url)
                response_data['robots_txt'] = 'Found' if response.status_code == 200 else 'Not Found'
            except requests.exceptions.RequestException:
                response_data['robots_txt'] = 'Error'

        # 2. Check SSL
        def check_ssl(website_url):
            response_data['ssl_enabled'] = website_url.startswith("https")
            if response_data['ssl_enabled']:
                hostname = website_url.replace("https://", "").replace("http://", "").split("/")[0]
                context = ssl.create_default_context()
                try:
                    with socket.create_connection((hostname, 443)) as sock:
                        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                            cert = ssock.getpeercert()
                            expiration_date = datetime.datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                            days_left = (expiration_date - datetime.datetime.utcnow()).days
                            response_data['expiration_date'] = expiration_date.strftime("%Y-%m-%d")
                            response_data['days_left'] = days_left
                            response_data['is_valid'] = days_left > 0
                except Exception as e:
                    response_data['ssl_error'] = str(e)

        # 3. Analyze Meta Tags
        def analyze_meta_tags(website_url):
            try:
                response = requests.get(website_url)
                soup = BeautifulSoup(response.content, 'html.parser')
                title = soup.find("title").get_text() if soup.find("title") else None
                response_data['title'] = title
                response_data['title_length'] = len(title) if title else 0
                
                meta_desc = soup.find("meta", attrs={"name": "description"})
                desc_content = meta_desc["content"] if meta_desc else ""
                response_data['meta_description'] = desc_content
                response_data['meta_description_length'] = len(desc_content)
                
                response_data['title_feedback'] = (
                    "Great! Maintain the same title length" if 70 <= response_data['title_length'] <= 156 else
                    "Your title length is too short!" if response_data['title_length'] < 70 else
                    "Your title length is too long!"
                )

                response_data['meta_description_feedback'] = (
                    "Great! Maintain the same description length" if 120 <= response_data['meta_description_length'] <= 160 else
                    "Your description length is too short!" if response_data['meta_description_length'] < 120 else
                    "Your description length is too long!"
                )
            except Exception as e:
                response_data['meta_tags_error'] = str(e)

        # 4. Social Media Links Check
        def check_social_links(website_url):
            options = Options()
            options.add_argument("--headless")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

            driver.get(website_url)
            time.sleep(2)

            social_links = {
                "Facebook": False,
                "Instagram": False,
                "Twitter": False,
                "LinkedIn": False
            }

            for social in social_links.keys():
                social_links[social] = len(driver.find_elements(By.XPATH, f"//a[contains(@href, '{social.lower()}')]")) > 0

            response_data['social_links'] = social_links
            driver.quit()

        # 5. Check Local Business Schema
        def check_local_business_schema(website_url):
            try:
                response = requests.get(website_url)
                soup = BeautifulSoup(response.content, 'html.parser')
                script_tags = soup.find_all("script", type="application/ld+json")
                
                has_local_schema = any("LocalBusiness" in tag.get_text() for tag in script_tags)
                response_data['local_business_schema'] = has_local_schema
            except Exception as e:
                response_data['local_business_schema_error'] = str(e)

        # 6. Google Analytics Check
        def check_google_analytics(website_url):
            try:
                response = requests.get(website_url)
                response_data['google_analytics'] = "gtag('config'" in response.text or "UA-" in response.text
            except Exception as e:
                response_data['google_analytics_error'] = str(e)

        # 7. Analyze Links
        def analyze_links(website_url):
            response = requests.get(website_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            all_links = soup.find_all('a', href=True)
            
            internal_links = set()
            external_links = set()
            duplicate_links = set()
            
            for link in all_links:
                href = link['href']
                if website_url in href or href.startswith('/'):
                    if href in internal_links:
                        duplicate_links.add(href)
                    internal_links.add(href)
                else:
                    if href in external_links:
                        duplicate_links.add(href)
                    external_links.add(href)

            response_data['total_links'] = len(all_links)
            response_data['internal_links'] = len(internal_links)
            response_data['external_links'] = len(external_links)
            response_data['duplicate_links'] = len(duplicate_links)

        # 8. Keyword Analysis
        def keyword_analysis(website_url, keyword):
            response = requests.get(website_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            text_content = soup.get_text().lower()
            keyword_count = text_content.count(keyword.lower())
            
            data = {
                "Keyword": [keyword],
                "Count": [keyword_count]
            }
            df = pd.DataFrame(data)
            response_data['keyword_analysis'] = df.to_html(classes="table table-striped", index=False)

        # 9. Sitemap Check
        def check_sitemap(website_url):
            sitemap_url = f"{website_url}/sitemap.xml"
            try:
                response = requests.get(sitemap_url)
                response_data['sitemap'] = 'Found' if response.status_code == 200 else 'Not Found'
            except requests.exceptions.RequestException:
                response_data['sitemap'] = 'Error'

        # 10. Header Tags Analysis
        def analyze_header_tags(website_url):
            response = requests.get(website_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            headers = Counter(tag.name for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
            response_data['header_tags'] = dict(headers)

            h1_tags = [h1.get_text().strip() for h1 in soup.find_all('h1')]
            response_data['h1_content'] = h1_tags

        # 11. Alt Tags Count
        def count_alt_tags(website_url):
            response = requests.get(website_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            images = soup.find_all('img')
            alt_count = sum(1 for img in images if img.get('alt'))
            non_alt_count = len(images) - alt_count
            response_data['alt_tags'] = {
                'alt_tag_count': alt_count,
                'non_alt_tag_count': non_alt_count
            }

        # 12. Content Length
        def count_content_amount(website_url):
            response = requests.get(website_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            content = soup.get_text()
            response_data['content_length'] = len(content)

        # Execute all checks
        check_robots_txt(website_url)
        check_ssl(website_url)
        analyze_meta_tags(website_url)
        check_social_links(website_url)
        check_local_business_schema(website_url)
        check_google_analytics(website_url)
        analyze_links(website_url)
        keyword_analysis(website_url, keywords)
        check_sitemap(website_url)
        analyze_header_tags(website_url)
        count_alt_tags(website_url)
        count_content_amount(website_url)

        return Response(response_data, status=status.HTTP_200_OK)


class UserRegisterAPI(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        user = User.objects.create_user(username=username, password=password, email=email)
        return Response({'message': 'User created successfully'}, status=status.HTTP_201_CREATED)

