const { DataTypes, Model } = require('sequelize');
const { sequelize } = require('../../../db');

class PmsPatentReview extends Model {}

PmsPatentReview.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    applicationId: {
      type: DataTypes.INTEGER,
      allowNull: false,
      references: {
        model: 'pms_patent_applications',
        key: 'id',
      },
      onDelete: 'CASCADE',
    },
    reviewerId: {
      type: DataTypes.INTEGER,
      allowNull: false,
      references: {
        model: 'users',
        key: 'id',
      },
    },
    reviewerRole: {
      type: DataTypes.ENUM('Director', 'Committee', 'Attorney', 'Admin'),
      allowNull: false,
      defaultValue: 'Director',
    },
    decision: {
      type: DataTypes.ENUM('Approve', 'Reject', 'Needs Revision', 'File Patent', 'Do Not File', 'Needs Amendment'),
      allowNull: false,
    },
    justification: {
      type: DataTypes.TEXT,
      allowNull: false,
    },
    reviewVersion: {
      type: DataTypes.INTEGER,
      allowNull: false,
      defaultValue: 1,
    },
  },
  {
    sequelize,
    tableName: 'pms_patent_reviews',
    timestamps: true,
    indexes: [{ fields: ['applicationId'] }, { fields: ['reviewerId'] }],
  },
);

module.exports = PmsPatentReview;
