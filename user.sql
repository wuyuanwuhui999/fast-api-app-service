/*
 Navicat Premium Data Transfer

 Source Server         : 本机mysql
 Source Server Type    : MySQL
 Source Server Version : 80024
 Source Host           : localhost:3306
 Source Schema         : play

 Target Server Type    : MySQL
 Target Server Version : 80024
 File Encoding         : 65001

 Date: 10/08/2025 13:39:09
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for user
-- ----------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user`  (
  `id` varchar(32) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL COMMENT '主键id',
  `user_account` varchar(20) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL COMMENT '账号',
  `password` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL COMMENT '密码',
  `create_date` datetime(0) NULL DEFAULT NULL COMMENT '创建时间',
  `update_date` datetime(0) NULL DEFAULT NULL COMMENT '更新时间',
  `username` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL COMMENT '昵称',
  `telephone` varchar(20) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '电话',
  `email` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '邮箱',
  `avater` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '头像地址',
  `birthday` varchar(16) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '出生年月日',
  `sex` varchar(1) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '性别，0:男，1:女',
  `role` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '角色',
  `sign` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '个性签名',
  `region` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '地区',
  `disabled` int(0) NULL DEFAULT 0 COMMENT '是否禁用，0表示不不禁用，1表示禁用',
  `permission` int(0) NULL DEFAULT 0 COMMENT '权限大小',
  PRIMARY KEY (`id`, `user_account`) USING BTREE,
  INDEX `id`(`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Compact;

-- ----------------------------
-- Records of user
-- ----------------------------
INSERT INTO `user` VALUES ('021b623183f047ec917f2900a56cbaec', '半夏时光', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:46:09', '2020-01-11 18:46:12', '半夏时光', '15302686947', '405873709@qq.com', '/static/user/avater/半夏时光.jpg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('1773f002c2b34903906e95a5ee554cef', '我就看看不下单', '202cb962ac59075b964b07152d234b70', '2025-03-02 22:31:33', '2025-03-02 22:31:33', '我就看看不下单', '', '123@qq.com', NULL, '', '0', NULL, '', '', 0, 0);
INSERT INTO `user` VALUES ('1947a0c2f5bd4385873b77f93fd2b269', 'wenqiang', 'e10adc3949ba59abbe56e057f20f883e', '2025-03-11 01:47:26', '2025-03-11 01:48:04', 'wuwenqiang2', '', '275018725@qq.com', NULL, '', '0', NULL, '', '深圳', 0, 0);
INSERT INTO `user` VALUES ('19e6fc89b59d4fc3a5a83e5b2fb4b6e8', '離別的抽泣', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:51:33', '2024-02-23 21:27:02', '離別的抽泣3', '15302686947', '405873725@qq.com', '/static/user/avater/離別的抽泣.jpg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('1a46a9d20a904fe0a2512f0299c556a6', '飞颜尘雪', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:48:28', '2020-01-11 18:48:31', '飞颜尘雪', '15302686947', '405873728@qq.com', '/static/user/avater/飞颜尘雪.jpg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('3f99b4e428e548c1b0436bdfdc15514b', '123', 'e10adc3949ba59abbe56e057f20f883e', '2024-01-20 00:44:24', '2024-01-20 00:44:24', '123', '123', '405873701@qq.com', NULL, '2024-01-02', '0', NULL, '123', '123', 0, 0);
INSERT INTO `user` VALUES ('45d39bd2876b4bbb967a393e498f2577', '且听风铃', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:54:22', '2024-01-21 10:56:13', '且听风铃2', '15302686947', '405873707@qq.com', '/static/user/avater/且听风铃.jpg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('4a187d448c1043eb9d1bd1f747b6a3f2', 'wuwenqiang', 'e10adc3949ba59abbe56e057f20f883e', '2025-03-09 23:30:20', '2025-03-09 23:30:20', 'wuwenqiang', '', '405873717', NULL, '', '0', NULL, '', '', 0, 0);
INSERT INTO `user` VALUES ('4bfd4d8272764b48a2c4cc5a0e76433d', '空城旧梦', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:50:23', '2023-04-21 23:52:38', '空城旧梦', '15302686947', '405873721@qq.com', '/static/user/avater/空城旧梦.jpg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('4cf36692882f4741b785760e8112398c', '落落清欢', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:52:15', '2024-04-25 22:40:20', '落落清欢', '15302686947', '405873723@qq.com', '/static/user/avater/落落清欢.jpg', '1990-10-8', '0', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('5ab2ba0bdee54462a8d0cf5f0491419f', '归去如风', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:49:43', '2020-01-11 18:49:47', '归去如风', '15302686947', '405873716@qq.com', '/static/user/avater/归去如风.jpg', '1990-10-8', '0', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('620a9c7782804e62a83d901fedb9dc71', '半岛弥音', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-18 18:41:52', '2020-01-11 18:41:57', '半岛弥音', '15302686947', '405873710@qq.com', '/static/user/avater/半岛弥音.jpg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('6765749bf601444ea68bdb788de4bab0', '吴怨吴悔', 'e10adc3949ba59abbe56e057f20f883e', '2019-08-13 00:00:00', '2025-02-02 20:13:16', '吴怨吴悔2', '15302686947', '4058737171@qq.com', '/static/user/avater/吴怨吴悔.jpg', '1990-10-10', '0', 'admin', '无怨，有悔', NULL, 0, 1);
INSERT INTO `user` VALUES ('6ac90a306e184391aee8d31e8f24bd8c', '吴尽吴穷', 'e10adc3949ba59abbe56e057f20f883e', '2019-08-19 00:59:28', '2019-08-19 00:59:32', '吴尽吴穷', '15302686947', '405873711@qq.com', '/static/user/avater/吴怨吴悔.jpg', '1990-10-8', '0', 'public', '无穷无尽的爱', NULL, 0, 0);
INSERT INTO `user` VALUES ('6de89ba997914e328384b92e1a524cd3', '雨晨清风', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:57:53', '2024-01-10 23:16:14', '雨晨清风', '15302686947', '405873726@qq.com', '/static/user/avater/雨晨清风.jpg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('9b86129c43bb4e1c9ee4ff8030e78e08', '孤影倾城', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:49:08', '2024-02-25 23:27:01', '孤影倾城', '15302686947', '405873715@qq.com', '/static/user/avater/孤影倾城.jpg', '1990-10-8', '1', 'public', '无怨，有悔', '深圳', 0, 0);
INSERT INTO `user` VALUES ('9c8be405b6a64a9084a30574b4cc1382', '逆夏光年', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:53:40', '2020-01-11 18:53:42', '逆夏光年', '15302686947', '405873724@qq.com', '/static/user/avater/逆夏光年.jpg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('b03c8f1176854790859dfda07fdf817d', '秋水天长', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:55:00', '2024-04-21 17:29:57', '秋水天长2', '15302686947', '405873720@qq.com', '/static/user/avater/秋水天长.jpg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('b3fadf144a5c43d7b51692594dc3fab9', '夕颜泪痕', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:55:53', '2020-01-11 18:55:56', '夕颜泪痕', '15302686947', '405873714@qq.com', '/static/user/avater/夕颜泪痕.jpg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('c01dfa9f29ee437f878f43eac54dcb30', '离殇荡情', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:50:58', '2020-01-11 18:51:01', '离殇荡情', '15302686947', '405873719@qq.com', '/static/user/avater/离殇荡情.jpeg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('c095ac9c7f50413f95fb304d9f15f6cb', 'wuwenqiang1', 'e10adc3949ba59abbe56e057f20f883e', '2025-03-09 23:48:22', '2025-03-09 23:48:22', 'wuwenqiang', '', '4968737171@qq.com', NULL, '', '0', NULL, '', '', 0, 0);
INSERT INTO `user` VALUES ('cf0b5ab3bb254d978220689bb590af6d', '初晓微芒', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:47:01', '2020-01-11 18:47:03', '初晓微芒', '15302686947', '405873708@qq.com', '/static/user/avater/初晓微芒.jpg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('db599c22607e4c85acc441a483209586', '灯火阑珊', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:47:39', '2024-02-25 15:42:22', '灯火阑珊2', '15302686947', '405873718@qq.com', '/static/user/avater/灯火阑珊.jpg', '1989-10-08', '1', 'public', '无怨，有悔', '深圳', 0, 0);
INSERT INTO `user` VALUES ('dd586713ef8740beb6f6d57b35010c63', '吴忧吴虑', 'e10adc3949ba59abbe56e057f20f883e', '2019-08-13 21:01:56', '2019-08-13 21:02:02', '吴忧吴虑', '15302686947', '405873712@qq.com', '/static/user/avater/吴怨吴悔.jpg', '1990-10-8', '0', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('f312546127eb4518a6937ecd0324be28', '落寞雨季', 'e10adc3949ba59abbe56e057f20f883e', '2020-01-11 18:53:02', '2022-12-18 00:11:04', '落寞雨季', '15302686947', '405873722@qq.com', '/static/user/avater/落寞雨季.jpg', '1990-10-8', '1', 'public', '无怨，有悔', NULL, 0, 0);
INSERT INTO `user` VALUES ('f71d6c016fa94cd29f9db53f71ec7b62', '吴时吴刻', '25d55ad283aa400af464c76d713c07ad', '2019-08-12 00:00:00', '2025-08-03 13:14:25', '吴时吴刻', '15302686947', '405873717@qq.com', '/static/user/avater/吴时吴刻.jpg', '1990-10-8', '0', 'public', '无时无刻不想你', NULL, 0, 0);

SET FOREIGN_KEY_CHECKS = 1;
