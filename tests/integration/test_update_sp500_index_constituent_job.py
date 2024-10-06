from app.mkt_data.update_index_constituents import SP500IndexConstituentsUpdater


def test_save_constituents():
    sp500_index_constituents_updater = SP500IndexConstituentsUpdater()
    sp500_index_constituents_updater.main()
