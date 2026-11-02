const { DataTypes, Model } = require('sequelize');
const { sequelize } = require('../../../db');

const DEFAULT_CATEGORIES = [
  { name: 'Utility Patent', description: 'Inventions with functional innovations.' },
  { name: 'Design Patent', description: 'Inventions focused on ornamental design.' },
  { name: 'Process Patent', description: 'Inventions focused on process improvements.' },
];

class PmsPatentCategory extends Model {
  static getDefaultCategories() {
    return DEFAULT_CATEGORIES;
  }

  static async seedDefaults() {
    for (const category of DEFAULT_CATEGORIES) {
      await this.findOrCreate({
        where: { name: category.name },
        defaults: category,
      });
    }
    return this.findAll({ order: [['name', 'ASC']] });
  }
}

PmsPatentCategory.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    name: {
      type: DataTypes.STRING(120),
      allowNull: false,
      unique: true,
    },
    description: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    isActive: {
      type: DataTypes.BOOLEAN,
      allowNull: false,
      defaultValue: true,
    },
  },
  {
    sequelize,
    tableName: 'pms_patent_categories',
    timestamps: true,
    indexes: [{ fields: ['name'] }],
  },
);

module.exports = PmsPatentCategory;
