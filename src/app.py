from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.auth_cookie import auth_backend, fastapi_users
from src.auth.models import User, Task, Team, TeamTask
from src.auth.schemas import UserRead, UserCreate, TaskCreate, TaskUpdate, TeamCreate, TeamUserAdd, TeamUserDelete, \
    TeamTaskCreate, TeamTaskUpdate
from src.database import get_async_session

app = FastAPI(title="Tasker")
current_user = fastapi_users.current_user()

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/api/auth/jwt",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/api/auth",
    tags=["auth"],
)


@app.post("/api/tasks_create")
async def create_task(
        task: TaskCreate,
        current_user: User = Depends(current_user),
        db: AsyncSession = Depends(get_async_session)):
    new_task = Task(
        title=task.title,
        description=task.description,
        priority=task.priority,
        due_date=task.due_date,
        creator_id=current_user.id,
        created_at=datetime.utcnow(),
        status=task.status
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task


@app.post("/api/tasks_update")
async def update_task(
        task_update: TaskUpdate,
        current_user: User = Depends(current_user),
        db: AsyncSession = Depends(get_async_session)
):
    # Получаем задачу по ID
    result = await db.execute(select(Task).where(Task.id == task_update.id, Task.creator_id == current_user.id))
    task = result.scalars().first()

    # Если задача не найдена, возвращаем ошибку 404
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Обновляем поля, если они переданы в запросе
    if task_update.title is not None:
        task.title = task_update.title
    if task_update.description is not None:
        task.description = task_update.description
    if task_update.due_date is not None:
        task.due_date = task_update.due_date
    if task_update.priority is not None:
        task.priority = task_update.priority
    if task_update.status is not None:
        task.status = task_update.status

    # Сохраняем изменения
    await db.commit()
    await db.refresh(task)
    return task


@app.post("/api/tasks_delete")
async def delete_task(
        task_id: int,
        current_user: User = Depends(current_user),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.creator_id == current_user.id))
    task = result.scalars().first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found or you're not the creator")

    await db.delete(task)
    await db.commit()
    return {"message": "Task deleted successfully"}

@app.post("/api/teams_create")
async def create_team(
    team: TeamCreate,
    current_user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session)
):
    new_team = Team(
        name=team.name,
        leader_id=current_user.id,
        members=[current_user.id]
    )
    db.add(new_team)
    await db.commit()
    await db.refresh(new_team)
    return new_team


@app.post("/api/teams_delete")
async def delete_team(
        team_id: int,
        current_user: User = Depends(current_user),
        db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(Team).where(Team.id == team_id, Team.leader_id == current_user.id))
    team = result.scalars().first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found or you're not the leader")

    await db.delete(team)
    await db.commit()
    return {"message": "Team and associated tasks deleted successfully"}

@app.post("/api/teams/add_member")
async def add_member(
    team_add: TeamUserAdd,
    current_user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session)
):
    # Проверка, что команда существует и текущий пользователь — лидер
    team = await db.execute(select(Team).where(Team.id == team_add.id, Team.leader_id == current_user.id))
    team = team.scalars().first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found or you're not the team leader")

    # Поиск пользователя по username
    user_result = await db.execute(select(User).where(User.username == team_add.username))
    user_to_add = user_result.scalars().first()

    if not user_to_add:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверка, что пользователь ещё не в команде
    if user_to_add.id in team.members:
        raise HTTPException(status_code=400, detail="User is already a team member")

    updated_members = team.members.copy()  # Создаем копию текущего списка
    updated_members.append(user_to_add.id)  # Добавляем нового участника
    team.members = updated_members  # Присваиваем обновленный список

    db.add(team)
    await db.commit()
    await db.refresh(team)
    return {"message": f"User {team_add.username} added to the team"}

@app.post("/api/teams/remove_member")
async def remove_member(
    team_del: TeamUserDelete,
    current_user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session)
):
    # Проверка, что команда существует и текущий пользователь — лидер
    team = await db.execute(select(Team).where(Team.id == team_del.id, Team.leader_id == current_user.id))
    team = team.scalars().first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found or you're not the team leader")

    # Поиск пользователя по username
    user_result = await db.execute(select(User).where(User.username == team_del.username))
    user_to_remove = user_result.scalars().first()

    if not user_to_remove:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверка, что пользователь состоит в команде
    if user_to_remove.id not in team.members:
        raise HTTPException(status_code=400, detail="User is not a team member")

    # Проверка, что лидер не удаляет сам себя
    if user_to_remove.id == team.leader_id:
        raise HTTPException(status_code=400, detail="Leader cannot remove themselves from the team")

    # Удаление пользователя из команды
    updated_members = team.members.copy()  # Копируем текущий список
    updated_members.remove(user_to_remove.id)  # Удаляем ID участника
    team.members = updated_members  # Присваиваем обновленный список

    db.add(team)
    await db.commit()
    await db.refresh(team)
    return {"message": f"User {team_del.username} removed from the team"}

@app.post("/api/teams/{team_id}/tasks", response_model=TeamTaskCreate)
async def create_team_task(
    team_id: int,
    task_data: TeamTaskCreate,
    current_user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session)
):
    # Проверка, что команда существует и текущий пользователь — лидер или участник
    team = await db.execute(select(Team).where(Team.id == team_id))
    team = team.scalars().first()
    if not team or current_user.id not in team.members:
        raise HTTPException(status_code=404, detail="Team not found or you're not a member")

    # Проверка, что указанный пользователь-исполнитель существует и является частью команды
    if task_data.assignee_id is not None:
        user_result = await db.execute(select(User).where(User.id == task_data.assignee_id))
        assignee_user = user_result.scalars().first()

        if not assignee_user:
            raise HTTPException(status_code=404, detail="Assignee user not found")

        if assignee_user.id not in team.members:
            raise HTTPException(status_code=400, detail="Assignee user is not a member of the team")

    # Создание новой задачи
    new_task = TeamTask(
        team_id=team_id,
        creator_id=current_user.id,
        assignee_id=task_data.assignee_id,
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
        status=task_data.status
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task

@app.post("/api/teams/tasks_update/{task_id}", response_model=TeamTaskUpdate)
async def update_team_task(
    task_id: int,
    task_data: TeamTaskUpdate,
    current_user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session)
):
    # Получение задачи
    task_query = await db.execute(select(TeamTask).where(TeamTask.id == task_id))
    task = task_query.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Получение команды
    team_query = await db.execute(select(Team).where(Team.id == task.team_id))
    team = team_query.scalars().first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Проверка прав на обновление
    is_leader_or_creator = current_user.id in [team.leader_id, task.creator_id]
    is_assignee_updating_status = task_data.status and current_user.id == task.assignee_id

    if not is_leader_or_creator and not is_assignee_updating_status:
        raise HTTPException(
            status_code=403,
            detail="Only the team leader, task creator, or assignee can update this task"
        )

    # Обновление полей задачи
    if is_leader_or_creator:
        if task_data.title is not None:
            task.title = task_data.title
        if task_data.description is not None:
            task.description = task_data.description
        if task_data.due_date is not None:
            task.due_date = task_data.due_date
        if task_data.assignee_id is not None:
            task.assignee_id = task_data.assignee_id

    # Обновление статуса задачи
    if task_data.status is not None:
        task.status = task_data.status

    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@app.post("/api/teams/tasks_delete/{task_id}", response_model=dict)
async def delete_team_task(
        task_id: int,
        current_user: User = Depends(current_user),
        db: AsyncSession = Depends(get_async_session)
):
    # Поиск задачи по ID
    task_result = await db.execute(select(TeamTask).where(TeamTask.id == task_id))
    task = task_result.scalars().first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Проверка, что текущий пользователь — лидер команды
    team = await db.execute(select(Team).where(Team.id == task.team_id, Team.leader_id == current_user.id))
    team = team.scalars().first()

    if not team:
        raise HTTPException(status_code=403, detail="Only the team leader can delete this task")

    # Удаление задачи
    await db.delete(task)
    await db.commit()

    return {"message": "Task deleted successfully"}

@app.get("/api/dashboard")
async def get_user_dashboard(current_user: User = Depends(current_user), db: AsyncSession = Depends(get_async_session)):
    # Получение задач текущего пользователя
    tasks_result = await db.execute(select(Task).where(Task.creator_id == current_user.id))
    my_tasks = tasks_result.scalars().all()

    # Получение команд, где текущий пользователь является лидером
    leader_teams_result = await db.execute(select(Team).where(Team.leader_id == current_user.id))
    leader_teams = leader_teams_result.scalars().all()

    # Получение команд, в которых текущий пользователь состоит (не является лидером)
    member_teams_result = await db.execute(
        select(Team).where(Team.members.cast(JSONB).contains([current_user.id]))  # Используем JSONB и оператор @>
    )
    member_teams = member_teams_result.scalars().all()
    # Формируем ответ
    response = {
        "my_tasks": my_tasks,
        "leader_teams": leader_teams,
        "member_teams": member_teams
    }

    return response

@app.get("/api/teams_tasks/{team_id}")
async def get_team_tasks(team_id: int, current_user: User = Depends(current_user), db: AsyncSession = Depends(get_async_session)):
    # Проверка, что команда существует и пользователь является её членом
    team_result = await db.execute(select(Team).where(Team.id == team_id, Team.members.cast(JSONB).contains([current_user.id])))
    team = team_result.scalars().first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found or you're not a member")

    # Получение всех задач для указанной команды
    task_result = await db.execute(select(TeamTask).where(TeamTask.team_id == team_id))
    team_tasks = task_result.scalars().all()

    return team_tasks



app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT","*"],
    allow_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Headers", "Access-Control-Allow-Origin",
                   "Authorization","*"],
)

