/**
 * JavaScript 简单测试文件 - Git推送演示
 */

function testAddition() {
    const result = 1 + 1;
    console.assert(result === 2, '加法测试失败');
    console.log('✓ 加法测试通过');
}

function testString() {
    const text = 'Hello from JavaScript!';
    console.assert(text.includes('Hello'), '字符串测试失败');
    console.log(`✓ 字符串测试通过: ${text}`);
}

function testArray() {
    const fruits = ['苹果', '香蕉', '橙子'];
    console.assert(fruits.length === 3, '数组长度测试失败');
    console.assert(fruits.includes('香蕉'), '数组包含测试失败');
    console.log(`✓ 数组测试通过: ${fruits.join(', ')}`);
}

function testObject() {
    const user = {
        name: 'Luna',
        age: 25,
        city: '北京'
    };
    console.assert(user.name === 'Luna', '对象属性测试失败');
    console.log(`✓ 对象测试通过: ${user.name}, ${user.age}岁, 来自${user.city}`);
}

function testAsync() {
    return new Promise((resolve) => {
        setTimeout(() => {
            console.log('✓ 异步测试通过 - 延迟执行成功');
            resolve();
        }, 100);
    });
}

function runAllTests() {
    console.log('运行 JavaScript 测试...\n');
    
    testAddition();
    testString();
    testArray();
    testObject();
    
    testAsync().then(() => {
        console.log('\n所有测试通过！✓');
    });
}

runAllTests();

module.exports = {
    testAddition,
    testString,
    testArray,
    testObject,
    testAsync
};
