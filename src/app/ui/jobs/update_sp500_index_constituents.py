from app import log
from app.mkt_data.update_index_constituents import SP500IndexConstituentsUpdater


def main():
    sp500_index_constituents_updater = SP500IndexConstituentsUpdater()
    sp500_index_constituents_updater.main()
    log.info("Finished updating S&P 500 index constituents")


if __name__ == "__main__":
    main()
