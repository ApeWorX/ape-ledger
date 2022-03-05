from ape_ledger.choices import AddressPromptChoice

from .conftest import TEST_ADDRESS


class TestAddressPromptChoice:
    def test_get_user_selected_account(self, mocker, mock_ethereum_app):
        mock_prompt = mocker.patch("ape_ledger.choices.click.prompt")
        choices = AddressPromptChoice(mock_ethereum_app)
        choices._choice_index = 1

        # `None` means the user hasn't selected yeet
        # And is entering other keys, possible the paging keys.
        mock_prompt_return_values = iter((None, None, None, None, TEST_ADDRESS, None))

        def _side_effect(*args, **kwargs):
            return next(mock_prompt_return_values)

        mock_prompt.side_effect = _side_effect
        address, hdpath = choices.get_user_selected_account()
        assert address == TEST_ADDRESS
        assert str(hdpath) == "m/44'/60'/1'/0/0"
