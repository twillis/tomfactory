"""The queue (FR-161): a request made while another run holds the line waits its turn, and starts by itself when the
run before it is merged, or ended any other way than needing the operator.

The operator, 2026-11-26: "It also allows us to get more work queued up for the factory, in the viewer there's only
ever one run in a lane"; refined with him the same day: `factory request` queues; the next starts once the run before
is merged (or ended rejected or abandoned); a run that ends needing him holds the line; first in, first out; abandon
removes a queued request; one queue for the whole factory."""
import pytest

from factory import driver, operations, records
from factory.store import open_store
from tests.conftest import drive_with, git, PLAN, script
from tests.fake_agent import FakeAgent


def states(home):
    return [(r.id, r.state, r.outcome) for r in open_store(home).query("runs", order="id")]


def waiting(target, text="Create a hello page"):
    """A request carried to where its plan waits for approval."""
    drive_with(FakeAgent([{"envelope": PLAN}]))
    return operations.request(text, target)


@pytest.mark.fr("FR-161")
def test_a_request_made_while_a_run_is_open_waits_its_turn_first_in_first(home, target, fake_notify):
    first = waiting(target)
    second = operations.request("Run 2, second: another thing", target)
    third = operations.request("Run 3, third: one more", target)
    assert (second.state, third.state) == ("queued", "queued")
    assert [r.id for r in records.queued(open_store(home))] == [second.id, third.id]
    assert not operations.Workspace.of(second).path.exists()          # no checkout until it starts
    assert records.open_run(open_store(home)).id == first.id


@pytest.mark.fr("FR-161")
def test_the_next_starts_by_itself_when_the_run_before_is_abandoned(home, target, fake_notify):
    first = waiting(target)
    second = operations.request("Run 2, second: another thing", target)
    drive_with(FakeAgent([{"envelope": PLAN}]))                 # the agent that plans the second, when it starts
    operations.abandon(first.id)
    run = open_store(home).get("runs", second.id)
    assert run.state == "awaiting_approval"           # it started, and its plan is waiting
    assert [e.kind for e in records.events_after(open_store(home), second.id)].count("started_from_queue") == 1


@pytest.mark.fr("FR-161")
def test_an_accepted_run_holds_the_line_until_it_is_merged(home, target, fake_notify):
    drive_with(FakeAgent(script()))
    first = operations.approve(operations.request("Create a hello page", target).id)
    assert first.outcome == "accepted", first.reason
    second = operations.request("Run 2, second: another thing", target)
    assert second.state == "queued"
    assert "not yet merged" in operations.held_by(open_store(home))
    operations.status()                                         # any operation looks; nothing to start yet
    assert open_store(home).get("runs", second.id).state == "queued"
    git(target, "merge", "-q", "--no-ff", "-m", "merge", first.branch)
    drive_with(FakeAgent([{"envelope": PLAN}]))
    operations.status()                                         # the next operation starts it
    assert open_store(home).get("runs", second.id).state == "awaiting_approval"
    assert open_store(home).get("runs", second.id).base_commit == git(target, "rev-parse", "HEAD")


@pytest.mark.fr("FR-161")
def test_a_run_that_ended_needing_you_holds_the_line_until_abandoned(home, target, fake_notify):
    first = waiting(target)
    second = operations.request("Run 2, second: another thing", target)
    driver.end_run(open_store(home), first.id, "needs-me", "interrupted")
    operations.status()
    assert open_store(home).get("runs", second.id).state == "queued"
    assert "needing you" in operations.held_by(open_store(home))
    drive_with(FakeAgent([{"envelope": PLAN}]))
    set_aside = operations.abandon(first.id)
    assert (set_aside.outcome, set_aside.reason.startswith("abandoned after it ended needing you")) == ("rejected", True)
    assert open_store(home).get("runs", second.id).state == "awaiting_approval"


@pytest.mark.fr("FR-161")
def test_abandon_takes_a_queued_request_out_of_the_line(home, target, fake_notify):
    first = waiting(target)
    second = operations.request("Run 2, second: another thing", target)
    third = operations.request("Run 3, third: one more", target)
    gone = operations.abandon(second.id)
    assert (gone.state, gone.outcome, gone.reason) == ("ended", "rejected", "abandoned before it started")
    assert [r.id for r in records.queued(open_store(home))] == [third.id]
    assert records.open_run(open_store(home)).id == first.id          # the open run is untouched


@pytest.mark.fr("FR-161")
def test_a_queued_request_that_can_no_longer_start_ends_needing_you(home, target, fake_notify):
    first = waiting(target)
    second = operations.request("Run 2, second: another thing", target)
    git(target, "rm", "-q", ".factory.toml")
    git(target, "commit", "-q", "-m", "settings gone")
    operations.abandon(first.id)
    run = open_store(home).get("runs", second.id)
    assert (run.state, run.outcome) == ("ended", "needs-me")
    assert run.reason.startswith("the queued request could not start")
