"""
Neo4j 图数据库初始化脚本

用于向 Neo4j 导入 README 中描述的电商商品知识图谱示例数据，包含以下节点与关系：
  节点: Product, Category, Supplier, Customer, Order, Review
  关系: BELONGS_TO, SUPPLIED_BY, CONTAINS, PLACED, WROTE, ABOUT

运行前请确认：
  1. Neo4j 已启动（可用 docker compose up -d 或本地安装）
  2. llm_backend/.env 中已配置 NEO4J_URL / NEO4J_USERNAME / NEO4J_PASSWORD / NEO4J_DATABASE
  3. 已安装依赖: pip install neo4j

运行方式（在仓库根目录执行）：
  python llm_backend/scripts/init_neo4j.py
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent  # llm_backend/，app 包位于此目录
sys.path.insert(0, str(ROOT_DIR))

from neo4j import GraphDatabase
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(service="init_neo4j")


def build_sample_data():
    """构造示例电商数据（与 README 中的结构一致）"""
    categories = [
        {"CategoryID": 1, "CategoryName": "智能音箱", "Description": "具备语音助手的智能音箱设备"},
        {"CategoryID": 2, "CategoryName": "智能家电", "Description": "可联网控制的家用电器"},
        {"CategoryID": 3, "CategoryName": "智能穿戴", "Description": "可穿戴的智能设备"},
    ]

    suppliers = [
        {"SupplierID": 1, "CompanyName": "声学科技", "ContactName": "张伟", "Phone": "13800000001"},
        {"SupplierID": 2, "CompanyName": "智家电器", "ContactName": "李娜", "Phone": "13800000002"},
    ]

    products = [
        {"ProductID": 1, "ProductName": "小智音箱 Pro", "UnitPrice": 399.0, "UnitsInStock": 120,
         "UnitsOnOrder": 50, "QuantityPerUnit": "1台", "Discontinued": False,
         "CategoryID": 1, "SupplierID": 1},
        {"ProductID": 2, "ProductName": "小智音箱 Mini", "UnitPrice": 199.0, "UnitsInStock": 300,
         "UnitsOnOrder": 0, "QuantityPerUnit": "1台", "Discontinued": False,
         "CategoryID": 1, "SupplierID": 1},
        {"ProductID": 3, "ProductName": "智控空调", "UnitPrice": 2599.0, "UnitsInStock": 40,
         "UnitsOnOrder": 20, "QuantityPerUnit": "1台", "Discontinued": False,
         "CategoryID": 2, "SupplierID": 2},
    ]

    customers = [
        {"CustomerID": 1, "CompanyName": "个人用户A", "ContactName": "王芳"},
        {"CustomerID": 2, "CompanyName": "个人用户B", "ContactName": "陈强"},
    ]

    orders = [
        {"OrderID": 1, "OrderDate": "2025-01-15", "CustomerID": 1, "ProductID": 1},
        {"OrderID": 2, "OrderDate": "2025-02-20", "CustomerID": 2, "ProductID": 3},
    ]

    reviews = [
        {"ReviewID": 1, "ReviewText": "音质很好，语音识别准确", "Rating": 5,
         "ReviewDate": "2025-01-18", "CustomerID": 1, "ProductID": 1},
        {"ReviewID": 2, "ReviewText": "制冷快，但有点吵", "Rating": 4,
         "ReviewDate": "2025-02-25", "CustomerID": 2, "ProductID": 3},
    ]

    return categories, suppliers, products, customers, orders, reviews


def main():
    uri = settings.NEO4J_URL
    user = settings.NEO4J_USERNAME
    password = settings.NEO4J_PASSWORD
    database = settings.NEO4J_DATABASE

    logger.info(f"正在连接 Neo4j: {uri} (database={database})")
    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        driver.verify_connectivity()
    except Exception as e:
        logger.error(f"无法连接 Neo4j，请确认服务已启动且 .env 配置正确: {e}")
        sys.exit(1)

    categories, suppliers, products, customers, orders, reviews = build_sample_data()

    with driver.session(database=database) as session:
        # 清空已有示例数据，避免重复导入
        session.run("MATCH (n) DETACH DELETE n")

        # 创建节点
        for c in categories:
            session.run(
                "CREATE (n:Category {CategoryID:$id, CategoryName:$name, Description:$desc})",
                id=c["CategoryID"], name=c["CategoryName"], desc=c["Description"])
        for s in suppliers:
            session.run(
                "CREATE (n:Supplier {SupplierID:$id, CompanyName:$name, ContactName:$contact, Phone:$phone})",
                id=s["SupplierID"], name=s["CompanyName"], contact=s["ContactName"], phone=s["Phone"])
        for p in products:
            session.run(
                """CREATE (n:Product {
                    ProductID:$id, ProductName:$name, UnitPrice:$price,
                    UnitsInStock:$stock, UnitsOnOrder:$ordered,
                    QuantityPerUnit:$qty, Discontinued:$disc})""",
                id=p["ProductID"], name=p["ProductName"], price=p["UnitPrice"],
                stock=p["UnitsInStock"], ordered=p["UnitsOnOrder"],
                qty=p["QuantityPerUnit"], disc=p["Discontinued"])
        for c in customers:
            session.run(
                "CREATE (n:Customer {CustomerID:$id, CompanyName:$name, ContactName:$contact})",
                id=c["CustomerID"], name=c["CompanyName"], contact=c["ContactName"])
        for o in orders:
            session.run(
                "CREATE (n:Order {OrderID:$id, OrderDate:$date})",
                id=o["OrderID"], date=o["OrderDate"])
        for r in reviews:
            session.run(
                "CREATE (n:Review {ReviewID:$id, ReviewText:$text, Rating:$rating, ReviewDate:$date})",
                id=r["ReviewID"], text=r["ReviewText"], rating=r["Rating"], date=r["ReviewDate"])

        # 创建关系
        for p in products:
            session.run(
                "MATCH (p:Product {ProductID:$pid}), (c:Category {CategoryID:$cid}) "
                "CREATE (p)-[:BELONGS_TO]->(c)",
                pid=p["ProductID"], cid=p["CategoryID"])
            session.run(
                "MATCH (p:Product {ProductID:$pid}), (s:Supplier {SupplierID:$sid}) "
                "CREATE (p)-[:SUPPLIED_BY]->(s)",
                pid=p["ProductID"], sid=p["SupplierID"])
        for o in orders:
            session.run(
                "MATCH (o:Order {OrderID:$oid}), (p:Product {ProductID:$pid}) "
                "CREATE (o)-[:CONTAINS]->(p)",
                oid=o["OrderID"], pid=o["ProductID"])
            session.run(
                "MATCH (c:Customer {CustomerID:$cid}), (o:Order {OrderID:$oid}) "
                "CREATE (c)-[:PLACED]->(o)",
                cid=o["CustomerID"], oid=o["OrderID"])
        for r in reviews:
            session.run(
                "MATCH (c:Customer {CustomerID:$cid}), (rv:Review {ReviewID:$rid}) "
                "CREATE (c)-[:WROTE]->(rv)",
                cid=r["CustomerID"], rid=r["ReviewID"])
            session.run(
                "MATCH (rv:Review {ReviewID:$rid}), (p:Product {ProductID:$pid}) "
                "CREATE (rv)-[:ABOUT]->(p)",
                rid=r["ReviewID"], pid=r["ProductID"])

        # 校验
        counts = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt").data()
        logger.info(f"导入完成，节点统计: {counts}")

    driver.close()
    logger.info("Neo4j 初始化成功！可访问 http://localhost:7474 查看图谱。")


if __name__ == "__main__":
    main()
