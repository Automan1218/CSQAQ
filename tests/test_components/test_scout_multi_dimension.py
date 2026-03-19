from csqaq.components.agents.scout import cross_filter_ranks


class TestCrossFilterRanksVariadic:
    def test_two_lists_overlap(self):
        price_ids = [1, 2, 3, 4, 5]
        vol_ids = [3, 4, 5, 6, 7]
        result = cross_filter_ranks(price_ids, vol_ids, min_overlap=2)
        assert 3 in result
        assert 4 in result
        assert 5 in result

    def test_three_lists_overlap(self):
        list_a = [1, 2, 3, 4, 5]
        list_b = [3, 4, 5, 6, 7]
        list_c = [4, 5, 8, 9, 10]
        result = cross_filter_ranks(list_a, list_b, list_c, min_overlap=3)
        assert 4 in result
        assert 5 in result
        assert 3 not in result  # only in 2 lists

    def test_min_overlap_2_with_backfill(self):
        list_a = [1, 2, 3]
        list_b = [4, 5, 6]
        # No overlap at min_overlap=2, should backfill from first list
        result = cross_filter_ranks(list_a, list_b, min_overlap=2)
        assert len(result) >= 5  # backfill ensures at least 5

    def test_single_list(self):
        result = cross_filter_ranks([1, 2, 3, 4, 5], min_overlap=1)
        assert result == [1, 2, 3, 4, 5]

    def test_empty_lists(self):
        result = cross_filter_ranks([], [], min_overlap=2)
        assert result == []
