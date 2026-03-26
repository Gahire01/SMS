from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError 
from ..models.attendance_model import AttendanceModel
from ..schemas.attendance_schema import AttendanceSchema 
from ..extentions import db, jwt


attendance_router = Blueprint("attendance_router",__name__)

@attendance_router.route("/mark-attendance", methods=["POST"])
@jwt_required()
def mark_attendance():
    try:
        schema = AttendanceSchema()
        data = schema.load(request.get_json() or request.form)

        attendance_date = data.get('date')

        # Upsert by (student_id, date) so re-saving attendance on the same day
        # updates the existing row instead of failing on unique constraint.
        existing_attendance = AttendanceModel.query.filter_by(
            student_id=data['student_id'],
            date=attendance_date,
        ).first()

        if existing_attendance:
            existing_attendance.status = data['status']
            attendance = existing_attendance
            message = "Attendance updated successfully"
            status_code = 200
        else:
            attendance = AttendanceModel(
                student_id=data['student_id'],
                date=attendance_date,
                status=data['status']
            )
            db.session.add(attendance)
            message = "Attendance marked successfully"
            status_code = 201

        db.session.commit()
        
        return jsonify({"message": message, "attendance_id": attendance.attendance_id}), status_code
    
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "messages": err.messages}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to mark attendance", "message": str(e)}), 500


@attendance_router.route("/get-attendance", methods=["GET"])
@jwt_required()
def get_attendance():

    attendance = AttendanceModel.query.all()
    attendance_list = []

    for att in attendance:
        attendance_info = {
            "id": att.attendance_id,
            "student_id": att.student_id,
            "date": att.date.isoformat() if att.date else None,
            "status": att.status
        }

        attendance_list.append(attendance_info)
        
    return jsonify({"attendance": attendance_list}), 200


@attendance_router.route("/update-attendance/<int:attendance_id>", methods=["PUT"])
@jwt_required()
def update_attendance(attendance_id):
    try:
        attendance = AttendanceModel.query.get(attendance_id)

        if not attendance:
            return jsonify({"message": "Attendance not found"}), 404
        
        schema = AttendanceSchema(partial=True)
        data = schema.load(request.get_json() or request.form)
        
        for key, value in data.items():
            setattr(attendance, key, value)

        db.session.commit()

        return jsonify({"message": f"Attendance {attendance_id} updated successfully"}), 200
    
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "messages": err.messages}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update attendance", "message": str(e)}), 500



@attendance_router.route("/delete-attendance/<int:attendance_id>", methods=["DELETE"])
@jwt_required()
def delete_attendance(attendance_id):

    attendance = AttendanceModel.query.get(attendance_id)

    if not attendance:
        return jsonify({"message": "Attendance not found"}), 404
    
    db.session.delete(attendance)
    db.session.commit()

    return jsonify({"message": f"Attendance {attendance_id} deleted successfully"}), 200