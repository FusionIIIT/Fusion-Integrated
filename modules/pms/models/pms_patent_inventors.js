const { DataTypes, Model } = require('sequelize');
const { sequelize } = require('../../../db');

class PmsPatentInventor extends Model {
  static normalizeShare(value) {
    const numeric = Number(value || 0);
    if (Number.isNaN(numeric)) {
      return 0;
    }
    return Number(numeric.toFixed(2));
  }
}

PmsPatentInventor.init(
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
    inventorId: {
      type: DataTypes.INTEGER,
      allowNull: true,
      references: {
        model: 'users',
        key: 'id',
      },
    },
    inventorName: {
      type: DataTypes.STRING(180),
      allowNull: false,
    },
    inventorEmail: {
      type: DataTypes.STRING(180),
      allowNull: true,
    },
    ownershipShare: {
      type: DataTypes.DECIMAL(6, 2),
      allowNull: false,
      defaultValue: 0,
      set(value) {
        this.setDataValue('ownershipShare', PmsPatentInventor.normalizeShare(value));
      },
    },
    consentProvided: {
      type: DataTypes.BOOLEAN,
      allowNull: false,
      defaultValue: false,
    },
    agreementSigned: {
      type: DataTypes.BOOLEAN,
      allowNull: false,
      defaultValue: false,
    },
  },
  {
    sequelize,
    tableName: 'pms_patent_inventors',
    timestamps: true,
    indexes: [{ fields: ['applicationId'] }],
  },
);

module.exports = PmsPatentInventor;
