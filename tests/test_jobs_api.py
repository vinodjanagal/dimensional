import uuid

import pytest

from app.models import Formula, Job, Note, User


# ---------------------------------------------------------------- helpers

async def _make_note(db, user, title="Test", content="hello world"):
    note = Note(owner_id=user.id, title=title, content=content)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


# ---------------------------------------------------------------- enqueue

@pytest.mark.asyncio
async def test_enqueue_analysis_returns_202(
    authenticated_client, test_user, db, fake_arq
):
    note = await _make_note(db, test_user)

    response = await authenticated_client.post(f"/notes/{note.id}/analyze")
    assert response.status_code == 202

    body = response.json()
    assert body["status"] == "queued"
    job_id = uuid.UUID(body["job_id"])

    # Row was created
    job = await db.get(Job, job_id)
    assert job is not None
    assert job.note_id == note.id
    assert job.user_id == test_user.id
    assert job.status == "queued"

    # Job was enqueued with correct arguments
    assert len(fake_arq.enqueued) == 1
    fn_name, kwargs = fake_arq.enqueued[0]
    assert fn_name == "analyze_note"
    assert kwargs["note_id"] == note.id
    assert kwargs["user_id"] == test_user.id
    assert kwargs["job_id"] == str(job_id)


@pytest.mark.asyncio
async def test_enqueue_analysis_unknown_note_404(
    authenticated_client, fake_arq
):
    response = await authenticated_client.post("/notes/99999/analyze")
    assert response.status_code == 404
    assert fake_arq.enqueued == []


@pytest.mark.asyncio
async def test_enqueue_analysis_other_users_note_404(
    authenticated_client, db, fake_arq
):
    other = User(email="other@example.com", password_hash="x")
    db.add(other)
    await db.commit()
    await db.refresh(other)

    note = Note(owner_id=other.id, title="x", content="x")
    db.add(note)
    await db.commit()
    await db.refresh(note)

    response = await authenticated_client.post(f"/notes/{note.id}/analyze")
    assert response.status_code == 404
    assert fake_arq.enqueued == []


# ---------------------------------------------------------------- status

@pytest.mark.asyncio
async def test_get_job_returns_status(authenticated_client, test_user, db):
    note = await _make_note(db, test_user)

    job = Job(
        note_id=note.id,
        user_id=test_user.id,
        job_type="note_analysis",
        status="done",
        result={"word_count": 2},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    response = await authenticated_client.get(f"/jobs/{job.id}")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "done"
    assert body["result"]["word_count"] == 2
    assert body["error"] is None


@pytest.mark.asyncio
async def test_get_job_unknown_404(authenticated_client):
    response = await authenticated_client.get(f"/jobs/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_jobs_for_note(authenticated_client, test_user, db):
    note = await _make_note(db, test_user)

    for i in range(3):
        db.add(
            Job(
                note_id=note.id,
                user_id=test_user.id,
                job_type="note_analysis",
                status="done",
                result={"i": i},
            )
        )
    await db.commit()

    response = await authenticated_client.get(f"/notes/{note.id}/jobs")
    assert response.status_code == 200
    assert len(response.json()) == 3


# ---------------------------------------------------------------- task logic

@pytest.mark.asyncio
async def test_analyze_note_task_counts_words(test_user, db):
    from app.jobs.tasks import _run_analysis

    note = await _make_note(
        db, test_user, content="one two three four five"
    )

    result = await _run_analysis(db, note.id)
    assert result["word_count"] == 5
    assert result["char_count"] == 23
    assert result["line_count"] == 1


@pytest.mark.asyncio
async def test_analyze_note_task_reports_invalid_formula(test_user, db):
    """E = m * v has dimension of momentum, not energy. Should be flagged."""
    from app.jobs.tasks import _run_analysis
    from app.repositories import unit_repository

    note = await _make_note(db, test_user, content="x")
    joule = await unit_repository.get_by_symbol(db, "J")
    assert joule is not None

    bad = Formula(
        note_id=note.id,
        name="wrong_energy",
        expression="kg * m / s",
        result_unit_id=joule.id,
    )
    db.add(bad)
    await db.commit()

    result = await _run_analysis(db, note.id)
    assert result["formula_count"] == 1
    assert len(result["invalid_formulas"]) == 1
    assert result["invalid_formulas"][0]["name"] == "wrong_energy"
    assert "dimension" in result["invalid_formulas"][0]["reason"]


@pytest.mark.asyncio
async def test_analyze_note_task_reports_valid_formula(test_user, db):
    from app.jobs.tasks import _run_analysis
    from app.repositories import unit_repository

    note = await _make_note(db, test_user, content="x")
    joule = await unit_repository.get_by_symbol(db, "J")

    good = Formula(
        note_id=note.id,
        name="kinetic_energy",
        expression="kg * (m / s) ** 2",
        result_unit_id=joule.id,
    )
    db.add(good)
    await db.commit()

    result = await _run_analysis(db, note.id)
    assert result["formula_count"] == 1
    assert result["invalid_formulas"] == []