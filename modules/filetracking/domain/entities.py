"""Pure Python domain entities for File Tracking System (FTS).

No Django, no DRF, no Celery imports.
"""
from dataclasses import dataclass, field
from datetime import datetime

from .rules import (
    assert_current_holder,
    assert_operational_actor,
    validate_forward_recipient,
    validate_initial_comment,
    validate_movement_comment,
    validate_return_recipient,
)
from .state_machine import (
    FileLifecycleState,
    MovementType,
    assert_can_archive,
    assert_can_discard_draft,
    assert_can_edit_draft,
    assert_can_forward_or_return,
    assert_can_transition,
)


@dataclass
class AttachmentInfo:
    id: int | None = None
    file_name: str = ""
    file_path: str = ""
    uploaded_by_id: int = 0
    uploaded_at: datetime | None = None


@dataclass
class CommentRecord:
    id: int | None = None
    author_id: int = 0
    author_role: str = ""
    comment_text: str = ""
    created_at: datetime | None = None


@dataclass
class MovementRecord:
    id: int | None = None
    movement_type: MovementType = MovementType.CREATION
    sender_id: int = 0
    sender_role: str = ""
    receiver_id: int = 0
    receiver_role: str = ""
    comment: str = ""
    timestamp: datetime | None = None
    attachments: list[AttachmentInfo] = field(default_factory=list)


@dataclass
class FileComposite:
    """The aggregate root representing an FTS File (BR-FTS-003)."""

    id: int | None
    file_code: str
    subject: str
    description: str
    creator_id: int
    creator_role: str
    owner_id: int
    current_holder_id: int
    state: FileLifecycleState = FileLifecycleState.DRAFT
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None
    movements: list[MovementRecord] = field(default_factory=list)
    attachments: list[AttachmentInfo] = field(default_factory=list)
    comments: list[CommentRecord] = field(default_factory=list)

    @classmethod
    def create_new_draft(
        cls,
        subject: str,
        description: str,
        creator_id: int,
        creator_role: str,
        initial_comment: str,
        is_system_admin: bool = False,
        attachments: list[AttachmentInfo] | None = None,
    ) -> "FileComposite":
        """Create a new file in DRAFT state (FTS-UC-001, BR-FTS-001, BR-FTS-004)."""
        assert_operational_actor(is_system_admin)
        clean_comment = validate_initial_comment(initial_comment)

        initial_attachment_list = attachments or []

        return cls(
            id=None,
            file_code="",
            subject=subject.strip(),
            description=description.strip(),
            creator_id=creator_id,
            creator_role=creator_role,
            owner_id=creator_id,
            current_holder_id=creator_id,
            state=FileLifecycleState.DRAFT,
            comments=[
                CommentRecord(
                    author_id=creator_id,
                    author_role=creator_role,
                    comment_text=clean_comment,
                )
            ],
            attachments=initial_attachment_list,
        )

    def edit_draft(
        self,
        actor_id: int,
        subject: str | None = None,
        description: str | None = None,
        new_comment: str | None = None,
        is_system_admin: bool = False,
    ) -> None:
        """Edit a pre-circulation draft (FTS-UC-002, BR-FTS-005)."""
        assert_operational_actor(is_system_admin)
        assert_can_edit_draft(self.state)
        if actor_id != self.creator_id:
            from .errors import UnauthorizedFileActionError
            raise UnauthorizedFileActionError("Only the draft creator can edit this draft.")

        if subject is not None and subject.strip():
            self.subject = subject.strip()
        if description is not None:
            self.description = description.strip()
        if new_comment is not None and new_comment.strip():
            clean_c = validate_initial_comment(new_comment)
            if self.comments:
                self.comments[0].comment_text = clean_c
            else:
                self.comments.append(
                    CommentRecord(
                        author_id=actor_id,
                        author_role=self.creator_role,
                        comment_text=clean_c,
                    )
                )

    def discard_draft(self, actor_id: int, is_system_admin: bool = False) -> None:
        """Discard pre-circulation draft (FTS-UC-002, BR-FTS-005, AFR-FTS-016)."""
        assert_operational_actor(is_system_admin)
        assert_can_discard_draft(self.state)
        if actor_id != self.creator_id:
            from .errors import UnauthorizedFileActionError
            raise UnauthorizedFileActionError("Only the draft creator can discard this draft.")

    def forward(
        self,
        sender_id: int,
        sender_role: str,
        receiver_id: int,
        receiver_role: str,
        comment: str,
        attachments: list[AttachmentInfo] | None = None,
        is_system_admin: bool = False,
    ) -> MovementRecord:
        """Forward / send file to another employee (FTS-UC-003, CFR-FTS-005)."""
        assert_operational_actor(is_system_admin)
        assert_can_forward_or_return(self.state)
        assert_current_holder(sender_id, self.current_holder_id)
        validate_forward_recipient(receiver_id, sender_id)
        clean_comment = validate_movement_comment(comment)

        # Transition state if from draft to circulated
        if self.state == FileLifecycleState.DRAFT:
            assert_can_transition(self.state, FileLifecycleState.CIRCULATED)
            self.state = FileLifecycleState.CIRCULATED

        movement_attachments = attachments or []

        movement = MovementRecord(
            movement_type=MovementType.FORWARD,
            sender_id=sender_id,
            sender_role=sender_role,
            receiver_id=receiver_id,
            receiver_role=receiver_role,
            comment=clean_comment,
            attachments=movement_attachments,
        )

        self.movements.append(movement)
        self.comments.append(
            CommentRecord(
                author_id=sender_id,
                author_role=sender_role,
                comment_text=clean_comment,
            )
        )
        self.attachments.extend(movement_attachments)
        self.current_holder_id = receiver_id
        return movement

    def return_file(
        self,
        sender_id: int,
        sender_role: str,
        receiver_id: int,
        receiver_role: str,
        comment: str,
        attachments: list[AttachmentInfo] | None = None,
        is_system_admin: bool = False,
    ) -> MovementRecord:
        """Return received file to previous sender (FTS-UC-004, CFR-FTS-005)."""
        assert_operational_actor(is_system_admin)
        assert_can_forward_or_return(self.state)
        assert_current_holder(sender_id, self.current_holder_id)

        # Find previous sender from movements
        previous_sender_id = self.get_previous_sender_id()
        validate_return_recipient(receiver_id, previous_sender_id)
        clean_comment = validate_movement_comment(comment)

        movement_attachments = attachments or []

        movement = MovementRecord(
            movement_type=MovementType.RETURN,
            sender_id=sender_id,
            sender_role=sender_role,
            receiver_id=receiver_id,
            receiver_role=receiver_role,
            comment=clean_comment,
            attachments=movement_attachments,
        )

        self.movements.append(movement)
        self.comments.append(
            CommentRecord(
                author_id=sender_id,
                author_role=sender_role,
                comment_text=clean_comment,
            )
        )
        self.attachments.extend(movement_attachments)
        self.current_holder_id = receiver_id
        return movement

    def archive(self, user_id: int, is_system_admin: bool = False) -> None:
        """Archive completed circulated file by owner (FTS-UC-007, CFR-FTS-008, BR-FTS-012)."""
        assert_operational_actor(is_system_admin)
        assert_can_archive(self.state, user_id, self.owner_id)
        assert_can_transition(self.state, FileLifecycleState.ARCHIVED)
        self.state = FileLifecycleState.ARCHIVED

    def get_previous_sender_id(self) -> int | None:
        """Get the sender ID of the last recorded movement."""
        if not self.movements:
            return None
        return self.movements[-1].sender_id

    def get_associated_user_ids(self) -> list[int]:
        """All user IDs associated with this file (BR-FTS-009)."""
        ids = {self.creator_id, self.owner_id, self.current_holder_id}
        for m in self.movements:
            ids.add(m.sender_id)
            ids.add(m.receiver_id)
        for c in self.comments:
            ids.add(c.author_id)
        return sorted(ids)
