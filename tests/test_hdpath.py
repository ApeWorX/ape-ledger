import pytest

from ape_ledger.hdpath import HDAccountPath, HDBasePath, HDPath


class TestHDPath:
    include_subclasses = pytest.mark.parametrize("cls", (HDPath, HDBasePath, HDAccountPath))

    @include_subclasses
    def test_init_no_m_raises_value_errors(self, cls):
        path_without_m = "/44'/60'/0'/0"
        with pytest.raises(ValueError) as err:
            cls(path_without_m)

        assert str(err.value) == "HD path must begin with m/"

    @include_subclasses
    def test_account_path_trailing_slash_removes_trailing_slash(self, cls):
        path_with_trailing_slash = "m/44'/60'/0'/0/"
        path_obj = cls(path_with_trailing_slash)
        assert path_obj.path[-1] != "/"


class TestHDBasePath:
    def test_init_x_not_in_path_and_trailing_slash(self):
        # Edge case since the trailing slash is handled in super class
        # and when there is no {x} in the path, we append it to the end
        path_without_x_and_trailing_slash = "m/44'/60'/0'/0/"
        obj = HDBasePath(path_without_x_and_trailing_slash)
        actual = obj.path
        expected = "m/44'/60'/0'/0/{x}"
        assert actual == expected

    def test_get_account_path_x_in_path(self):
        path_with_x = "m/44'/60'/{x}'/0/0"
        obj = HDBasePath(path_with_x)
        actual = obj.get_account_path(3).path
        expected = "m/44'/60'/3'/0/0"
        assert actual == expected

    def test_get_account_path_x_not_in_path(self):
        path_without_x = "m/44'/60'/0'/0"
        obj = HDBasePath(path_without_x)
        actual = obj.get_account_path(3).path
        expected = "m/44'/60'/0'/0/3"
        assert actual == expected


class TestHDAccountPath:
    def test_as_bytes(self):
        path = HDAccountPath("m/44'/60'/2'/0/0")
        actual = path.as_bytes()
        expected = b"\x05\x80\x00\x00,\x80\x00\x00<\x80\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00"
        assert actual == expected
