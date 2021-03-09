import datetime
import csv
from nearest_dict import NearestDict
from etherscan import etherscan_gas, etherscan_timestamp

def read_csv(fn):
    with open(fn) as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            yield row

class EthereumEmissions():
    """
    Load the energy estimate from Digiconomist, and the gas
    measurement from Etherscan. Add some overhead like Offsetra.
    kgCO2/kWh is based on global 2019 mining pool distribution.
    """
    def __init__(self,
        date_to_kwh_fn='data/EECI_TWh - TWh per Year.csv',
        date_to_gas_fn='data/export-GasUsed.csv',
        kgco2_per_kwh=0.486,
        overhead=1.20):

        self.kgco2_per_kwh = kgco2_per_kwh
        self.overhead = overhead

        # https://digiconomist.net/ethereum-energy-consumption/
        date_to_kwh = {}
        for date, est_twh, min_twh in read_csv(date_to_kwh_fn):
            date = datetime.datetime.strptime(date, '%Y/%m/%d').date()
            try:
                # convert TWh/year to KWh/day
                kwh = 1e9 * float(est_twh) / 365
                date_to_kwh[date] = kwh
            except ValueError:
                continue
        self.date_to_kwh = NearestDict(date_to_kwh)

        # https://etherscan.io/chart/gasused?output=csv
        date_to_gas = {}
        for date, timestamp, gas in read_csv('data/export-GasUsed.csv'):
            date = datetime.datetime.strptime(date, '%m/%d/%Y').date()
            date_to_gas[date] = int(gas)
        self.date_to_gas = NearestDict(date_to_gas)

    def kgco2_per_gas(self, date):
        # weighted emissions factor based on mining pool distribution in 2019
        kwh_per_gas = self.date_to_kwh[date] / self.date_to_gas[date]
        return self.overhead * self.kgco2_per_kwh * kwh_per_gas

    def sum_kgco2(self, transactions):
        kgco2 = 0
        for tx in transactions:
            date = etherscan_timestamp(tx).date()
            gas = etherscan_gas(tx)
            kgco2 += self.kgco2_per_gas(date) * gas
        return kgco2