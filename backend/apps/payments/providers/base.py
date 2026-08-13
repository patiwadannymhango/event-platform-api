from abc import ABC, abstractmethod


class PaymentProviderInterface(ABC):

    @abstractmethod
    def create_card_collection(
        self,
        *,
        payment,
        customer,
    ):
        pass

    @abstractmethod
    def create_mobile_collection(
        self,
        *,
        payment,
        customer,
    ):
        pass

    @abstractmethod
    def get_payment_status(
        self,
        *,
        reference,
    ):
        pass

    @abstractmethod
    def get_wallet_balance(
        self,
    ):
        pass

    @abstractmethod
    def create_mobile_disbursement(
        self,
        *,
        withdrawal,
        destination,
    ):
        pass

    @abstractmethod
    def create_bank_disbursement(
        self,
        *,
        withdrawal,
        destination,
    ):
        pass

    @abstractmethod
    def get_disbursement_status(
        self,
        *,
        reference,
    ):
        pass