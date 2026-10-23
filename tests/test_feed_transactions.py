"""Owned in-memory feed failures must not publish a partial transition."""
from copy import deepcopy
import unittest
from src.continuation_coordinator import FeedStore, ContinuationSession
from src.model import MAX_EVENTS


def receipt(shard=0, lo=0, hi=2):
    return {'kind': 'events', 'shard': shard, 'epoch': 0, 'lo': lo, 'hi': hi,
            'events': [{'seq': n, 'shard': shard, 'changes': []} for n in range(lo+1, hi+1)]}


class FeedTransactionTests(unittest.TestCase):
    def test_late_wrong_shard_is_atomic_and_valid_retry_succeeds(self):
        feed = FeedStore()
        before = feed.logical_state()
        bad = receipt()
        bad['events'][-1]['shard'] = 1
        with self.assertRaises(ValueError):
            feed.accept(bad)
        self.assertEqual(feed.logical_state(), before)
        feed.accept(receipt())
        self.assertTrue(feed.covers(0, 0, 2))
        self.assertEqual(feed.receipt(0, 0, 2), receipt())

    def test_late_wrong_sequence_or_scalar_alias_is_atomic(self):
        for field, value in (('seq', 1), ('seq', True), ('seq', 2.0), ('shard', False)):
            feed = FeedStore()
            before = feed.logical_state()
            bad = receipt()
            bad['events'][-1][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                feed.accept(bad)
            self.assertEqual(feed.logical_state(), before)

    def test_receipt_scalar_aliases_and_short_batch_fail_without_mutation(self):
        for field, value in (('shard', False), ('shard', 0.0), ('epoch', False),
                             ('lo', False), ('hi', 2.0), ('hi', -1)):
            feed = FeedStore()
            bad = receipt()
            bad[field] = value
            before = feed.logical_state()
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                feed.accept(bad)
            self.assertEqual(feed.logical_state(), before)
        feed = FeedStore()
        bad = receipt()
        bad['events'].pop()
        with self.assertRaises(ValueError):
            feed.accept(bad)
        self.assertEqual(feed.frontiers, [0, 0, 0])

    def test_input_mutation_after_accept_cannot_change_stored_events(self):
        feed = FeedStore()
        source = receipt()
        feed.accept(source)
        expected = feed.logical_state()
        source['events'][0]['changes'].append(['owned', None])
        self.assertEqual(feed.logical_state(), expected)

    def test_late_bad_compaction_floor_is_atomic(self):
        feed = FeedStore()
        for shard in range(3):
            feed.accept(receipt(shard))
        before = feed.logical_state()
        for floors in ([1, 1, 3], [1, True, 1], [1, 1, 1.0]):
            with self.subTest(floors=floors), self.assertRaises(ValueError):
                feed.compact(floors)
            self.assertEqual(feed.logical_state(), before)
        feed.compact([1, 1, 1])
        self.assertEqual(feed.base, [1, 1, 1])
        self.assertTrue(all(set(events) == {2} for events in feed.events))

    def test_slowest_token_pins_history_and_reset_preserves_repair_window(self):
        feed = FeedStore()
        hi = MAX_EVENTS + 3
        feed.accept(receipt(0, 0, hi))
        session = ContinuationSession({}, feed)
        session.tokens = {'idle': {0: {'at': 0}}, 'current': {0: {'at': hi}}}
        self.assertEqual(session.minimum_frontiers(), [0, 0, 0])
        feed.compact(feed.safe_compaction_floors(session.minimum_frontiers()))
        self.assertEqual(len(feed.events[0]), hi)
        session.reset()
        feed.compact(feed.safe_compaction_floors(session.minimum_frontiers()))
        self.assertEqual(feed.base, [3, 0, 0])
        self.assertEqual(len(feed.events[0]), MAX_EVENTS)
        self.assertFalse(feed.covers(0, 0, hi))
        self.assertTrue(feed.covers(0, 3, hi))


if __name__ == '__main__':
    unittest.main()
