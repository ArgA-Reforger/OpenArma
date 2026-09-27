# Email

Email plugin providing email sending capabilities, supporting captchas, notifications, and other scenarios.

## Global Configuration

Add the following to `backend/core/conf.py`:

```python
##################################################
# [ Plugin ] email
##################################################
# .env
EMAIL_USERNAME: str
EMAIL_PASSWORD: str

# Basic configuration (in plugin.toml)
EMAIL_HOST: str
EMAIL_PORT: int
EMAIL_SSL: bool
EMAIL_CAPTCHA_REDIS_PREFIX: str
EMAIL_CAPTCHA_EXPIRE_SECONDS: int
```
