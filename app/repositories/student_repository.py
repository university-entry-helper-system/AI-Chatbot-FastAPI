from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from app.models.student import Student, StudentScore, StudentRanking, SubjectBlock, CrawlLog
from app.schemas.student import StudentCreate, StudentScoreCreate, StudentRankingCreate
from .base import BaseRepository

class StudentRepository(BaseRepository[Student]):
    def __init__(self):
        super().__init__(Student)
    
    def get_by_candidate_number(
        self, 
        db: Session, 
        candidate_number: str, 
        region: str = None
    ) -> Optional[Student]:
        query = db.query(Student).filter(Student.candidate_number == candidate_number)
        if region:
            query = query.filter(Student.region == region)
        return query.first()
    
    def create_or_update_student(self, db: Session, student_data: StudentCreate) -> Student:
        existing = self.get_by_candidate_number(
            db, student_data.candidate_number, student_data.region
        )
        
        if existing:
            # Update existing
            for field, value in student_data.model_dump().items():
                setattr(existing, field, value)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new
            return self.create(db, student_data.model_dump())
    
    def create_or_update_score(
        self, 
        db: Session, 
        student_id: int, 
        score_data: StudentScoreCreate
    ) -> StudentScore:
        existing = db.query(StudentScore).filter(
            and_(
                StudentScore.student_id == student_id,
                StudentScore.subject_code == score_data.subject_code
            )
        ).first()
        
        if existing:
            existing.subject_name = score_data.subject_name
            existing.score = score_data.score
            db.commit()
            db.refresh(existing)
            return existing
        else:
            score_dict = score_data.model_dump()
            score_dict["student_id"] = student_id
            db_score = StudentScore(**score_dict)
            db.add(db_score)
            db.commit()
            db.refresh(db_score)
            return db_score
    
    def create_or_update_subject_block(
        self,
        db: Session,
        block_code: str,
        block_name: str,
        block_id: int,
        subjects: List[str]
    ) -> SubjectBlock:
        existing = db.query(SubjectBlock).filter(
            SubjectBlock.block_code == block_code
        ).first()
        
        if existing:
            existing.block_name = block_name
            existing.block_id = block_id
            existing.subjects = subjects
            db.commit()
            db.refresh(existing)
            return existing
        else:
            block = SubjectBlock(
                block_code=block_code,
                block_name=block_name,
                block_id=block_id,
                subjects=subjects
            )
            db.add(block)
            db.commit()
            db.refresh(block)
            return block
    
    def create_or_update_ranking(
        self,
        db: Session,
        student_id: int,
        ranking_data: StudentRankingCreate
    ) -> StudentRanking:
        # Get block
        block = db.query(SubjectBlock).filter(
            SubjectBlock.block_code == ranking_data.block_code
        ).first()
        
        if not block:
            raise ValueError(f"Block {ranking_data.block_code} not found")
        
        existing = db.query(StudentRanking).filter(
            and_(
                StudentRanking.student_id == student_id,
                StudentRanking.block_id == block.id
            )
        ).first()
        
        ranking_dict = ranking_data.model_dump(exclude={"block_code"})
        ranking_dict["student_id"] = student_id
        ranking_dict["block_id"] = block.id
        
        if existing:
            for field, value in ranking_dict.items():
                setattr(existing, field, value)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            ranking = StudentRanking(**ranking_dict)
            db.add(ranking)
            db.commit()
            db.refresh(ranking)
            return ranking
    
    def get_student_detail(self, db: Session, student_id: int):
        student = db.query(Student).options(
            joinedload(Student.scores),
            joinedload(Student.rankings).joinedload(StudentRanking.block)
        ).filter(Student.id == student_id).first()
        
        if not student:
            return None
        
        # Convert to response format
        mark_info = [
            {"name": score.subject_name, "score": str(score.score)}
            for score in student.scores
        ]
        
        blocks = []
        for ranking in student.rankings:
            blocks.append({
                "label": ranking.block.block_name,
                "value": ranking.block.block_code,
                "id": ranking.block.block_id,
                "subjects": ranking.block.subjects,
                "point": ranking.total_point,
                "ranking": {
                    "equal": ranking.ranking_equal,
                    "higher": ranking.ranking_higher,
                    "total": ranking.ranking_total
                },
                "same2024": ranking.same_2024
            })
        
        return {
            "candidate_number": student.candidate_number,
            "mark_info": mark_info,
            "data_year": student.data_year,
            "blocks": blocks
        }
    
    def create_crawl_log(
        self,
        db: Session,
        candidate_number: str,
        region: str,
        success: bool,
        response_data: dict = None,
        error_message: str = None,
        response_time: float = None
    ) -> CrawlLog:
        log = CrawlLog(
            candidate_number=candidate_number,
            region=region,
            success=success,
            response_data=response_data,
            error_message=error_message,
            api_response_time=response_time
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

student_repository = StudentRepository()