from iso639 import Lang

FORMAT_PT1 = 0
FORMAT_FULL = 1


class Locale:
    """
    Singleton class for managing supported languages and ISO language codes.

    Provides functionality to handle language codes in both ISO 639-1 (two-letter)
    and full name formats.

    Attributes
    ----------
    _instance : Locale or None
        Singleton instance of the class
    _supported_languages : set
        Set of supported ISO 639-1 language codes

    Methods
    -------
    get_supported_languages(kind=FORMAT_PT1)
        Returns set of supported languages in specified format
    is_language_supported(language)
        Checks if a language is supported
    get_pt1_from_full(language)
        Converts full language name to ISO 639-1 code
    get_full_from_pt1(language, lower=True)
        Converts ISO 639-1 code to full language name
    """
    
    _instance = None

    def __new__(cls):
        """
        Creates or returns the singleton instance of Locale.

        Returns
        -------
        Locale
            The singleton instance
        """
        if cls._instance is None:
            cls._instance = super(Locale, cls).__new__(cls)
            cls._supported_languages = {'it','en'}
        return cls._instance

    def get_supported_languages(self, kind=FORMAT_PT1):
        """
        Returns set of supported languages in specified format.

        Parameters
        ----------
        kind : int, default=FORMAT_PT1
            Format type for returned language codes:
            - FORMAT_PT1: ISO 639-1 two-letter codes
            - FORMAT_FULL: Full language names

        Returns
        -------
        set
            Set of language codes or names

        Raises
        ------
        Exception
            If kind parameter is not implemented
        """
        if kind == FORMAT_PT1:
            return self._supported_languages.copy()
        elif kind == FORMAT_FULL:
            return {self.get_full_from_pt1(lang) for lang in self._supported_languages.copy()}
        raise Exception("Locale.get_supported_language() -> kind not implemented")
    
    def is_language_supported(self, language:str):
        """
        Checks if a language is in the supported languages set.

        Parameters
        ----------
        language : str
            Language code or name to check

        Returns
        -------
        bool
            True if language is supported, False otherwise
        """
        if len(language) > 2:
            language = Lang(language).pt1
        return language in self._supported_languages
    
    @staticmethod
    def get_pt1_from_full(language:str):
        """
        Converts full language name to ISO 639-1 code.

        Parameters
        ----------
        language : str
            Full language name

        Returns
        -------
        str
            ISO 639-1 two-letter language code
        """
        return Lang(name=language.capitalize()).pt1
    
    @staticmethod
    def get_full_from_pt1(language:str, lower:bool=True):
        """
        Converts ISO 639-1 code to full language name.

        Parameters
        ----------
        language : str
            ISO 639-1 two-letter language code
        lower : bool, default=True
            If True, returns lowercase name

        Returns
        -------
        str
            Full language name
        """
        return Lang(pt1=language).name if not lower else Lang(pt1=language).name.lower()
