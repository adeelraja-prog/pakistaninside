
import os
import requests


class StrategistAgent:

    def __init__(self):
        self.page_id = os.getenv("FACEBOOK_PAGE_ID")
        self.access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

        # Current Graph API version.
        # Can be changed through GitHub Actions environment variables.
        self.api_version = os.getenv(
            "FACEBOOK_GRAPH_API_VERSION",
            "v26.0"
        )

        self.base_url = (
            f"https://graph.facebook.com/{self.api_version}"
        )

        self.timeout = 60

    def run(self, image_path, caption):
        return self.publish_to_facebook(image_path, caption)

    def publish_to_facebook(self, image_path, caption):

        # Check Facebook credentials.
        if not self.page_id or not self.access_token:
            return {
                "error": "Facebook Page ID or Page Access Token is missing."
            }

        # Check image.
        if not image_path or not os.path.isfile(image_path):
            return {
                "error": f"Image file does not exist: {image_path}"
            }

        file_size = os.path.getsize(image_path)

        if file_size == 0:
            return {
                "error": "Generated image file is empty."
            }

        url = f"{self.base_url}/{self.page_id}/photos"

        payload = {
            "caption": caption,
            "published": "true",
            "access_token": self.access_token
        }

        try:
            print("[STRATEGIST] Connecting to Facebook Pages API...")

            with open(image_path, "rb") as image_file:

                files = {
                    "source": (
                        os.path.basename(image_path),
                        image_file,
                        "image/png"
                    )
                }

                response = requests.post(
                    url,
                    data=payload,
                    files=files,
                    timeout=self.timeout
                )

            try:
                result = response.json()
            except ValueError:
                return {
                    "error": (
                        "Facebook returned a non-JSON response. "
                        f"HTTP status: {response.status_code}"
                    )
                }

            # Facebook API errors.
            if response.status_code >= 400 or "error" in result:

                error_details = result.get("error", {})

                print(
                    "[STRATEGIST ERROR] Facebook publishing failed: "
                    f"{error_details}"
                )

                return {
                    "error": error_details or result,
                    "http_status": response.status_code
                }

            # Verify Facebook actually created the post.
            if not result.get("id") and not result.get("post_id"):
                return {
                    "error": (
                        "Facebook response did not contain a photo ID "
                        "or post ID."
                    ),
                    "response": result
                }

            print(
                "[STRATEGIST] Facebook publishing confirmed. "
                f"Response: {result}"
            )

            return result

        except requests.Timeout:
            return {
                "error": (
                    "Facebook request timed out. "
                    "Check the Page before retrying to avoid duplicates."
                )
            }

        except requests.RequestException as exc:
            return {
                "error": f"Facebook network request failed: {exc}"
            }

        except Exception as exc:
            return {
                "error": (
                    f"Unexpected Facebook publishing error: "
                    f"{type(exc).__name__}: {exc}"
                )
            }


    def publish_text_post(self, message):
        """Publish a text-only Page post using current Pages API permissions."""
        if not self.page_id or not self.access_token:
            return {"error": "Facebook Page ID or Page Access Token is missing."}
        url = f"{self.base_url}/{self.page_id}/feed"
        try:
            response = requests.post(
                url,
                data={"message": message, "access_token": self.access_token},
                timeout=self.timeout,
            )
            try:
                result = response.json()
            except ValueError:
                return {"error": "Facebook returned a non-JSON response.", "http_status": response.status_code}
            if response.status_code >= 400 or "error" in result or not result.get("id"):
                return {"error": result.get("error", result), "http_status": response.status_code}
            return result
        except requests.RequestException as exc:
            return {"error": f"Facebook text post failed: {exc}"}

    @classmethod
    def publish(cls, image_path, caption):
        agent = cls()
        return agent.publish_to_facebook(image_path, caption)
