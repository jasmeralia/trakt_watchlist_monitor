from pricing import meets_discount_threshold, select_best_quality


class TestSelectBestQuality:
    def test_prefers_uhd_over_hd_and_sd(self) -> None:
        prices = [
            {"quality": "SD", "price": 9.99},
            {"quality": "HD", "price": 12.99},
            {"quality": "UHD", "price": 14.99},
        ]
        result = select_best_quality(prices)
        assert result is not None
        assert result["quality"] == "UHD"

    def test_prefers_hd_over_sd(self) -> None:
        prices = [
            {"quality": "SD", "price": 9.99},
            {"quality": "HD", "price": 12.99},
        ]
        result = select_best_quality(prices)
        assert result is not None
        assert result["quality"] == "HD"

    def test_single_sd_entry(self) -> None:
        prices = [{"quality": "SD", "price": 9.99}]
        result = select_best_quality(prices)
        assert result is not None
        assert result["quality"] == "SD"

    def test_empty_list_returns_none(self) -> None:
        assert select_best_quality([]) is None


class TestMeetsDiscountThreshold:
    def test_above_threshold(self) -> None:
        assert meets_discount_threshold(10.00, 7.00, 20.0) is True  # 30% drop

    def test_exactly_at_threshold(self) -> None:
        assert meets_discount_threshold(10.00, 8.00, 20.0) is True  # exactly 20%

    def test_below_threshold(self) -> None:
        assert meets_discount_threshold(10.00, 9.00, 20.0) is False  # 10% drop

    def test_no_discount(self) -> None:
        assert meets_discount_threshold(10.00, 10.00, 20.0) is False
