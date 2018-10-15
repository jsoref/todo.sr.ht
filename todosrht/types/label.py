import sqlalchemy as sa
from srht.database import Base

class Label(Base):
    __tablename__ = 'label'

    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)

    tracker_id = sa.Column(sa.Integer,
            sa.ForeignKey("tracker.id"), nullable=False)
    tracker = sa.orm.relationship("Tracker", backref=sa.orm.backref("labels"))

    name = sa.Column(sa.Text, nullable=False)
    color = sa.Column(sa.Text, nullable=False)
    text_color = sa.Column(sa.Text, nullable=False)

    __table_args__ = (
        sa.UniqueConstraint("tracker_id", "name",
            name="idx_tracker_name_unique"),
    )

    def __repr__(self):
        return '<Label {} {}>'.format(self.id, self.name)
