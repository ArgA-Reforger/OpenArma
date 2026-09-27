import re


def search_string(pattern: str, text: str) -> re.Match[str]:
    """
    Match the entire field with a regular expression

    :param pattern: regular expression pattern
    :param text: text to match
    :return:
    """
    return re.search(pattern, text)


def match_string(pattern: str, text: str) -> re.Match[str]:
    """
    Match from the beginning of the field with a regular expression

    :param pattern: regular expression pattern
    :param text: text to match
    :return:
    """
    return re.match(pattern, text)


def is_phone(number: str) -> re.Match[str]:
    """
    Check the phone number format

    :param number: phone number to check
    :return:
    """
    phone_pattern = r'^1[3-9]\d{9}$'
    return match_string(phone_pattern, number)


def is_git_url(url: str) -> re.Match[str]:
    """
    Check the git URL format (only HTTP/HTTPS protocols are allowed)

    :param url: URL to check
    :return:
    """
    git_pattern = r'^(?P<scheme>https?)://(?P<host>[^/]*)(?P<path>(?:/[^/]*)*/)(?P<repo>[^/]+?)(?:\.git)?$'
    return match_string(git_pattern, url)


def is_has_number(value: str) -> re.Match[str]:
    """
    Check for a digit

    :param value: value to check
    :return:
    """
    number_pattern = r'\d'
    return search_string(number_pattern, value)


def is_has_letter(value: str) -> re.Match[str]:
    """
    Check for a letter

    :param value: value to check
    :return:
    """
    letter_pattern = r'[a-zA-Z]'
    return search_string(letter_pattern, value)


def is_has_special_char(value: str) -> re.Match[str]:
    """
    Check for a special character

    :param value: value to check
    :return:
    """
    special_char_pattern = r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]'
    return search_string(special_char_pattern, value)


def is_english_identifier(value: str) -> re.Match[str]:
    """
    Check for an English identifier

    :param value: value to check
    :return:
    """
    identifier_pattern = r'^[a-zA-Z][a-zA-Z_]*$'
    return match_string(identifier_pattern, value)
